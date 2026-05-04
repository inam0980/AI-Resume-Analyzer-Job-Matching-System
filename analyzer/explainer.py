"""
Advanced SHAP explainer + smart recommendation engine.

SHAP uses a TF-IDF + LogisticRegression pipeline trained on:
  - resume text (positive)
  - jd text (positive)
  - generic negative samples
This gives per-term contribution scores that explain WHY the match scored as it did.
"""

import re
import shap
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


# ── SHAP explainability ───────────────────────────────────────────────────────

_NEGATIVES = [
    "no relevant skills or experience listed",
    "generic candidate with vague background",
    "unrelated work history and education",
    "entry level applicant with no technical skills",
    "career change with no domain experience",
]


def build_shap_explanation(
    resume_text: str,
    jd_text: str,
    matched_skills: list,
    missing_skills: list,
) -> dict:
    try:
        texts  = [resume_text, jd_text] + _NEGATIVES
        labels = [1, 1] + [0] * len(_NEGATIVES)

        vec = TfidfVectorizer(
            max_features=300,
            stop_words='english',
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        X = vec.fit_transform(texts)

        clf = LogisticRegression(max_iter=1000, C=1.0)
        clf.fit(X, labels)

        resume_vec = vec.transform([resume_text])
        explainer  = shap.LinearExplainer(clf, X, feature_perturbation='interventional')
        shap_vals  = explainer.shap_values(resume_vec)

        feature_names = vec.get_feature_names_out()
        # shap_vals shape: (n_samples, n_features) or list thereof
        vals = np.array(shap_vals[0] if isinstance(shap_vals, list) else shap_vals[0])

        top_idx = np.argsort(np.abs(vals))[::-1][:20]
        top_features = [
            {'term': feature_names[i], 'impact': round(float(vals[i]), 4)}
            for i in top_idx
        ]

        return {
            'top_features':    top_features,
            'positive_impact': [f for f in top_features if f['impact'] > 0][:10],
            'negative_impact': [f for f in top_features if f['impact'] < 0][:10],
        }

    except Exception as exc:
        # Graceful fallback — still meaningful output
        pos = [{'term': s, 'impact':  0.5} for s in (matched_skills or [])[:10]]
        neg = [{'term': s, 'impact': -0.3} for s in (missing_skills or [])[:10]]
        return {
            'top_features':    pos + neg,
            'positive_impact': pos,
            'negative_impact': neg,
            'error': str(exc),
        }


# ── Smart recommendation engine ───────────────────────────────────────────────

_LEARNING_RESOURCES = {
    'python':          'Python – docs.python.org / Real Python',
    'javascript':      'JS – javascript.info / MDN Docs',
    'typescript':      'TypeScript – typescriptlang.org/docs',
    'java':            'Java – docs.oracle.com',
    'react':           'React – react.dev',
    'django':          'Django – djangoproject.com',
    'fastapi':         'FastAPI – fastapi.tiangolo.com',
    'docker':          'Docker – docs.docker.com',
    'kubernetes':      'Kubernetes – kubernetes.io/docs',
    'aws':             'AWS – aws.amazon.com/training',
    'azure':           'Azure – learn.microsoft.com',
    'gcp':             'GCP – cloud.google.com/learn',
    'machine learning':'ML – Coursera Andrew Ng / fast.ai',
    'deep learning':   'DL – fast.ai / d2l.ai',
    'tensorflow':      'TensorFlow – tensorflow.org/learn',
    'pytorch':         'PyTorch – pytorch.org/tutorials',
    'bert':            'BERT – Hugging Face course (huggingface.co)',
    'llm':             'LLMs – Hugging Face NLP course',
    'langchain':       'LangChain – python.langchain.com',
    'sql':             'SQL – sqlzoo.net / Mode Analytics',
    'postgresql':      'PostgreSQL – postgresql.org/docs',
    'mongodb':         'MongoDB – university.mongodb.com',
    'spark':           'Apache Spark – spark.apache.org/docs',
    'kafka':           'Kafka – kafka.apache.org/documentation',
    'git':             'Git – git-scm.com/doc',
    'linux':           'Linux – linuxcommand.org',
    'graphql':         'GraphQL – graphql.org/learn',
    'microservices':   'Microservices – microservices.io',
    'agile':           'Agile – atlassian.com/agile',
    'system design':   'System Design – github.com/donnemartin/system-design-primer',
}

_SECTION_TIPS = {
    'summary': (
        "Add a 3-4 sentence professional summary at the top of your resume "
        "that mirrors the job title and key requirements."
    ),
    'experience': (
        "For each role, lead with a strong action verb and quantify impact "
        "(e.g., 'Reduced latency by 40% by optimising query pipeline')."
    ),
    'skills': (
        "Create a dedicated Skills section with categories "
        "(Languages / Frameworks / Cloud / Tools) so ATS can scan it easily."
    ),
    'education': (
        "List relevant coursework, GPA (if strong), and any research or "
        "thesis work related to the target role."
    ),
}

_GENERAL_TIPS = [
    "Tailor your resume for each application — use the job description as a template.",
    "Keep your resume to 1-2 pages; use concise bullet points.",
    "Add links to GitHub, portfolio, or LinkedIn profile.",
    "Proofread carefully — grammar errors reduce perceived professionalism.",
    "Use ATS-friendly formatting: avoid tables, columns, or graphics.",
    "Include certifications (AWS, GCP, Coursera, etc.) relevant to the role.",
]


def generate_recommendations(
    matched_skills: list,
    missing_skills: list,
    match_score: float,
    critical_missing: list = None,
    keyword_analysis: dict = None,
    section_scores: dict = None,
    experience: dict = None,
) -> list:
    recs = []
    critical_missing = critical_missing or []
    keyword_analysis = keyword_analysis or {}
    section_scores   = section_scores or {}
    experience       = experience or {}

    # ── Experience mismatch ──
    if experience and not experience.get('match'):
        r_lvl = experience.get('resume_level', 'unknown')
        j_lvl = experience.get('jd_level', 'unknown')
        recs.append(
            f"Experience level mismatch detected — your resume signals '{r_lvl}' "
            f"but the JD targets '{j_lvl}'. "
            + ("Highlight leadership, mentoring, and system-design experience to bridge the gap."
               if j_lvl == 'senior' else
               "Emphasise your foundational skills and eagerness to learn.")
        )

    # ── Critical missing skills (highest priority) ──
    if critical_missing:
        top = critical_missing[:4]
        recs.append(
            f"Priority skill gap — add these to your resume ASAP: "
            f"{', '.join(top)}. "
            "These are core requirements for this role."
        )
        for skill in top[:2]:
            resource = _LEARNING_RESOURCES.get(skill)
            if resource:
                recs.append(f"Learn {skill}: {resource}")

    # ── Non-critical missing skills ──
    other_missing = [s for s in missing_skills if s not in critical_missing]
    if other_missing:
        recs.append(
            f"Add these skills if you have them (or plan to learn them): "
            f"{', '.join(other_missing[:5])}."
        )

    # ── Keyword gap ──
    missing_kw = keyword_analysis.get('missing_keywords', [])
    if missing_kw:
        recs.append(
            f"Include these JD keywords naturally in your resume: "
            f"{', '.join(missing_kw[:6])}."
        )

    # ── Weak sections ──
    for sec, score in section_scores.items():
        if score is not None and score < 45:
            tip = _SECTION_TIPS.get(sec)
            if tip:
                recs.append(f"Weak {sec.capitalize()} section (score {score}%): {tip}")

    # ── Score-based advice ──
    if match_score < 35:
        recs.append(
            "Your overall match is low. Consider rewriting your resume summary "
            "and experience bullets to mirror the job description's language."
        )
        recs.append(
            "Use the job description as a checklist — every bullet point in "
            "your resume should map to at least one requirement."
        )
    elif match_score < 60:
        recs.append(
            "Good foundation. Incorporate more keywords from the job description "
            "into your experience bullets and skills section."
        )
        recs.append(
            "Highlight 2-3 concrete achievements that directly match the top "
            "responsibilities listed in the JD."
        )
    else:
        recs.append(
            "Strong match! Write a targeted cover letter emphasising your "
            "top 3 matched skills with concrete examples."
        )
        recs.append(
            "Prepare to discuss specific projects where you used "
            f"{', '.join(matched_skills[:3])} in depth."
        )

    # ── General tips (fill up to 10) ──
    for tip in _GENERAL_TIPS:
        if len(recs) >= 10:
            break
        recs.append(tip)

    return recs[:10]
