"""
Advanced AI matching engine.

Pipeline:
1. Section-aware resume parsing  (Education / Experience / Skills / Summary)
2. Multi-model BERT ensemble      (mpnet-base-v2  +  multi-qa-mpnet-base-dot-v1)
3. FAISS semantic search          (per-section + full-doc)
4. TF-IDF keyword gap analysis    (exact JD keywords missing from resume)
5. Experience-level detection     (Junior / Mid / Senior mismatch penalty)
6. Weighted composite score       (semantic 40% | skills 30% | keywords 20% | experience 10%)
"""

import re
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer

# ── Model registry (lazy-loaded singletons) ──────────────────────────────────

_models: dict = {}

MODEL_NAMES = {
    'mpnet':    'all-mpnet-base-v2',          # strongest general BERT
    'multiqa':  'multi-qa-mpnet-base-dot-v1', # fine-tuned for query-doc matching
}


def _load(key: str) -> SentenceTransformer:
    if key not in _models:
        _models[key] = SentenceTransformer(MODEL_NAMES[key])
    return _models[key]


def _encode(model_key: str, text: str) -> np.ndarray:
    emb = _load(model_key).encode([text], convert_to_numpy=True, normalize_embeddings=True)
    return emb.astype('float32')


# ── FAISS inner-product similarity ───────────────────────────────────────────

def _faiss_score(a: np.ndarray, b: np.ndarray) -> float:
    dim = a.shape[1]
    idx = faiss.IndexFlatIP(dim)
    idx.add(b)
    dist, _ = idx.search(a, 1)
    return float(np.clip(dist[0][0], 0.0, 1.0))


# ── Section parser ────────────────────────────────────────────────────────────

SECTION_HEADERS = {
    'summary':    r'(summary|objective|profile|about)',
    'experience': r'(experience|work history|employment|career)',
    'education':  r'(education|academic|qualification|degree|university|college)',
    'skills':     r'(skills|technologies|tech stack|competencies|expertise)',
    'projects':   r'(projects|portfolio|work samples)',
    'certifications': r'(certif|licen|accredit)',
}


def parse_sections(text: str) -> dict:
    """Split resume text into named sections. Falls back to full text."""
    sections = {k: '' for k in SECTION_HEADERS}
    sections['full'] = text

    lines = text.split('\n')
    current = 'full'
    buf: dict = {k: [] for k in SECTION_HEADERS}
    buf['full'] = []

    for line in lines:
        clean = line.strip()
        matched_section = None
        for sec, pattern in SECTION_HEADERS.items():
            if re.match(pattern, clean.lower()):
                matched_section = sec
                break
        if matched_section:
            current = matched_section
        else:
            buf[current].append(clean)

    for sec in SECTION_HEADERS:
        sections[sec] = '\n'.join(buf[sec]).strip()
        if not sections[sec]:
            sections[sec] = text  # fallback so embeddings are never empty

    return sections


# ── Skill taxonomy ────────────────────────────────────────────────────────────

SKILL_GROUPS = {
    'languages': [
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
        'scala', 'kotlin', 'swift', 'r', 'matlab', 'perl', 'ruby', 'php',
    ],
    'frontend': [
        'react', 'angular', 'vue', 'nextjs', 'svelte', 'html', 'css',
        'bootstrap', 'tailwind', 'webpack', 'vite', 'sass',
    ],
    'backend': [
        'django', 'flask', 'fastapi', 'spring', 'spring boot', 'express',
        'nodejs', 'node.js', 'rails', 'laravel', 'asp.net',
    ],
    'databases': [
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
        'sqlite', 'cassandra', 'dynamodb', 'neo4j', 'firebase',
    ],
    'cloud_devops': [
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ansible',
        'jenkins', 'github actions', 'gitlab ci', 'ci/cd', 'helm', 'prometheus',
    ],
    'ml_ai': [
        'machine learning', 'deep learning', 'nlp', 'computer vision',
        'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy',
        'bert', 'transformers', 'llm', 'openai', 'langchain', 'hugging face',
        'xgboost', 'lightgbm', 'reinforcement learning',
    ],
    'data': [
        'spark', 'hadoop', 'kafka', 'airflow', 'dbt', 'power bi', 'tableau',
        'excel', 'looker', 'bigquery', 'snowflake',
    ],
    'tools': [
        'git', 'github', 'gitlab', 'jira', 'confluence', 'linux', 'bash',
        'graphql', 'rest api', 'microservices', 'grpc', 'rabbitmq',
    ],
    'practices': [
        'agile', 'scrum', 'kanban', 'tdd', 'bdd', 'oop', 'design patterns',
        'data structures', 'algorithms', 'system design', 'clean code',
    ],
    'soft_skills': [
        'communication', 'teamwork', 'leadership', 'problem solving',
        'critical thinking', 'time management', 'mentoring',
    ],
}

ALL_SKILLS = [s for group in SKILL_GROUPS.values() for s in group]

# Skills with higher weight because they're commonly pivotal in job matches
CRITICAL_SKILLS = set(SKILL_GROUPS['languages'] + SKILL_GROUPS['ml_ai'] + SKILL_GROUPS['cloud_devops'])


def extract_skills(text: str) -> dict:
    """Return {skill: group} for every skill found in text."""
    text_lower = text.lower()
    found = {}
    for group, skills in SKILL_GROUPS.items():
        for skill in skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                found[skill] = group
    return found


# ── Experience-level detector ─────────────────────────────────────────────────

LEVEL_SIGNALS = {
    'junior': [
        'junior', 'entry level', 'entry-level', 'fresher', 'graduate', '0-1 year',
        '0-2 year', '1 year', 'intern', 'trainee', 'associate',
    ],
    'mid': [
        'mid level', 'mid-level', '2-4 year', '3-5 year', '2+ year', '3+ year',
        'intermediate', 'software engineer', 'developer',
    ],
    'senior': [
        'senior', 'lead', 'principal', 'staff', 'architect', 'manager',
        '5+ year', '7+ year', '10+ year', '5-8 year', 'head of', 'director',
    ],
}


def detect_experience_level(text: str) -> str:
    text_lower = text.lower()
    scores = {level: 0 for level in LEVEL_SIGNALS}
    for level, signals in LEVEL_SIGNALS.items():
        for sig in signals:
            if sig in text_lower:
                scores[level] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'mid'


# ── TF-IDF keyword gap ────────────────────────────────────────────────────────

def keyword_gap_analysis(resume_text: str, jd_text: str) -> dict:
    """
    Find important JD keywords (by TF-IDF weight) that are absent from the resume.
    Also returns keywords present in both.
    """
    try:
        corpus = [jd_text, resume_text]
        vec = TfidfVectorizer(
            max_features=150,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
        )
        tfidf = vec.fit_transform(corpus)
        feature_names = vec.get_feature_names_out()
        jd_scores  = tfidf[0].toarray()[0]
        res_scores = tfidf[1].toarray()[0]

        # Top JD keywords by TF-IDF weight
        top_idx = np.argsort(jd_scores)[::-1][:40]
        jd_keywords  = [(feature_names[i], round(float(jd_scores[i]),  4)) for i in top_idx if jd_scores[i]  > 0]
        present      = [(kw, w) for kw, w in jd_keywords if res_scores[list(feature_names).index(kw)] > 0]
        missing      = [(kw, w) for kw, w in jd_keywords if res_scores[list(feature_names).index(kw)] == 0]

        return {
            'jd_top_keywords': [k for k, _ in jd_keywords[:20]],
            'present_keywords': [k for k, _ in present[:15]],
            'missing_keywords': [k for k, _ in missing[:15]],
            'keyword_coverage': round(len(present) / max(len(jd_keywords), 1) * 100, 1),
        }
    except Exception:
        return {
            'jd_top_keywords': [],
            'present_keywords': [],
            'missing_keywords': [],
            'keyword_coverage': 0.0,
        }


# ── Multi-model semantic scorer ───────────────────────────────────────────────

def semantic_score(resume_text: str, jd_text: str) -> dict:
    """
    Ensemble of two BERT models, each via FAISS.
    Returns per-model scores and weighted average.
    """
    scores = {}
    for key in MODEL_NAMES:
        r_emb = _encode(key, resume_text)
        j_emb = _encode(key, jd_text)
        scores[key] = _faiss_score(r_emb, j_emb)

    # mpnet weight 0.55, multiqa weight 0.45
    ensemble = scores['mpnet'] * 0.55 + scores['multiqa'] * 0.45
    return {
        'mpnet_score':   round(scores['mpnet']  * 100, 1),
        'multiqa_score': round(scores['multiqa'] * 100, 1),
        'ensemble':      round(ensemble * 100, 1),
    }


def section_semantic_scores(resume_sections: dict, jd_text: str) -> dict:
    """Score each parsed resume section against the full JD."""
    results = {}
    for sec in ['summary', 'experience', 'skills', 'education']:
        text = resume_sections.get(sec, '')
        if not text or text == resume_sections.get('full', ''):
            results[sec] = None
            continue
        r_emb = _encode('mpnet', text)
        j_emb = _encode('mpnet', jd_text)
        results[sec] = round(_faiss_score(r_emb, j_emb) * 100, 1)
    return results


# ── Main entry point ──────────────────────────────────────────────────────────

def compute_match(resume_text: str, jd_text: str) -> dict:
    # 1. Parse resume sections
    sections = parse_sections(resume_text)

    # 2. Multi-model semantic score (full doc)
    sem = semantic_score(resume_text, jd_text)

    # 3. Section-level semantic scores
    section_scores = section_semantic_scores(sections, jd_text)

    # 4. Skill analysis
    resume_skill_map = extract_skills(resume_text)
    jd_skill_map     = extract_skills(jd_text)

    resume_skills = set(resume_skill_map.keys())
    jd_skills     = set(jd_skill_map.keys())

    matched = sorted(resume_skills & jd_skills)
    missing = sorted(jd_skills - resume_skills)

    skill_coverage = len(matched) / max(len(jd_skills), 1)

    # Weight critical missing skills more heavily
    critical_missing = [s for s in missing if s in CRITICAL_SKILLS]

    # Skill score (penalise harder for missing critical skills)
    skill_score = skill_coverage * 100
    if critical_missing:
        penalty = min(15, len(critical_missing) * 3)
        skill_score = max(0, skill_score - penalty)

    # Group matched/missing by category for richer display
    matched_by_group = {}
    for s in matched:
        g = resume_skill_map[s]
        matched_by_group.setdefault(g, []).append(s)

    missing_by_group = {}
    for s in missing:
        g = jd_skill_map[s]
        missing_by_group.setdefault(g, []).append(s)

    # 5. Keyword gap
    kw = keyword_gap_analysis(resume_text, jd_text)

    # 6. Experience level
    resume_level = detect_experience_level(resume_text)
    jd_level     = detect_experience_level(jd_text)
    level_match  = resume_level == jd_level
    level_score  = 100.0 if level_match else (70.0 if abs(
        ['junior', 'mid', 'senior'].index(resume_level) -
        ['junior', 'mid', 'senior'].index(jd_level)
    ) == 1 else 40.0)

    # 7. Composite weighted score
    # semantic 40% | skills 30% | keywords 20% | experience 10%
    composite = (
        sem['ensemble']          * 0.40 +
        skill_score              * 0.30 +
        kw['keyword_coverage']   * 0.20 +
        level_score              * 0.10
    )
    composite = round(min(99.9, composite), 1)

    return {
        # Top-level
        'match_score':       composite,
        'matched_skills':    matched,
        'missing_skills':    missing,

        # Score breakdown
        'score_breakdown': {
            'semantic':    round(sem['ensemble'], 1),
            'skills':      round(skill_score, 1),
            'keywords':    kw['keyword_coverage'],
            'experience':  round(level_score, 1),
        },

        # Semantic detail
        'semantic': {
            'mpnet_score':   sem['mpnet_score'],
            'multiqa_score': sem['multiqa_score'],
            'ensemble':      sem['ensemble'],
        },

        # Section scores
        'section_scores': section_scores,

        # Skill detail
        'matched_by_group':   matched_by_group,
        'missing_by_group':   missing_by_group,
        'critical_missing':   critical_missing,
        'resume_skills':      sorted(resume_skills),
        'jd_skills':          sorted(jd_skills),
        'skill_coverage':     round(skill_coverage * 100, 1),

        # Keyword detail
        'keyword_analysis':   kw,

        # Experience
        'experience': {
            'resume_level': resume_level,
            'jd_level':     jd_level,
            'match':        level_match,
            'score':        round(level_score, 1),
        },
    }
