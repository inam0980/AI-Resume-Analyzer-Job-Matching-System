"""Gemini AI integration for resume analysis, suggestions, and rewriting."""
import json
import os
import re
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
_MODEL_NAME = 'gemini-2.5-flash'

if _API_KEY and _API_KEY != 'PASTE_YOUR_NEW_KEY_HERE':
    genai.configure(api_key=_API_KEY)


def _is_configured() -> bool:
    return bool(_API_KEY) and _API_KEY != 'PASTE_YOUR_NEW_KEY_HERE'


def _model():
    return genai.GenerativeModel(_MODEL_NAME)


def _extract_json(text: str):
    """Extract first JSON object/array from a model response."""
    if not text:
        return None
    fence = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def analyze_resume(resume_text: str, jd_text: str) -> dict:
    """Run a holistic AI analysis: score, skills, match %, and suggestions."""
    if not _is_configured():
        return {'error': 'Gemini API key not configured. Add GEMINI_API_KEY to .env file.'}

    prompt = f"""You are an expert resume reviewer and ATS specialist. Analyze the resume against the job description and return ONLY a JSON object with this exact schema:

{{
  "ai_score": <integer 0-100>,
  "match_percentage": <integer 0-100>,
  "extracted_skills": [<list of skills found in resume, max 25>],
  "required_skills": [<list of skills required by JD, max 20>],
  "matched_skills": [<skills present in both>],
  "missing_skills": [<skills in JD but not in resume>],
  "strengths": [<list of 3-5 resume strengths>],
  "weaknesses": [<list of 3-5 weak areas>],
  "improvement_suggestions": [<list of 6-10 specific actionable suggestions>],
  "weak_sections": {{
    "summary": <true/false>,
    "experience": <true/false>,
    "skills": <true/false>,
    "education": <true/false>
  }},
  "summary_feedback": "<2-3 sentences on overall fit>"
}}

RESUME:
{resume_text[:6000]}

JOB DESCRIPTION:
{jd_text[:3000]}

Return ONLY the JSON. No prose, no markdown."""

    try:
        response = _model().generate_content(prompt)
        data = _extract_json(response.text)
        if not data:
            return {'error': 'Could not parse AI response', 'raw': response.text[:500]}
        return data
    except Exception as e:
        return {'error': f'Gemini API error: {str(e)}'}


def rewrite_resume_sections(resume_text: str, jd_text: str, weak_sections: dict | None = None) -> dict:
    """Rewrite weak resume sections to better align with the JD."""
    if not _is_configured():
        return {'error': 'Gemini API key not configured.'}

    target = weak_sections or {'summary': True, 'experience': True, 'skills': True}
    sections_to_rewrite = [k for k, v in target.items() if v]
    if not sections_to_rewrite:
        sections_to_rewrite = ['summary', 'experience', 'skills']

    prompt = f"""You are a professional resume writer. Rewrite the specified sections of the resume to better match the job description. Use strong action verbs, quantifiable achievements, and relevant keywords.

Return ONLY a JSON object with this schema (only include keys for sections requested):
{{
  "summary": "<rewritten 3-4 sentence professional summary>",
  "experience": "<rewritten experience section with bullet points using \\n for line breaks, 5-8 bullets>",
  "skills": "<comma-separated, organized list of skills relevant to the JD>",
  "education": "<polished education section if requested>"
}}

Sections to rewrite: {', '.join(sections_to_rewrite)}

ORIGINAL RESUME:
{resume_text[:6000]}

TARGET JOB DESCRIPTION:
{jd_text[:3000]}

Return ONLY the JSON."""

    try:
        response = _model().generate_content(prompt)
        data = _extract_json(response.text)
        if not data:
            return {'error': 'Could not parse rewrite response', 'raw': response.text[:500]}
        return data
    except Exception as e:
        return {'error': f'Gemini API error: {str(e)}'}


def generate_full_rewritten_resume(resume_text: str, jd_text: str, candidate_name: str = '') -> dict:
    """Produce a full polished resume tailored to the JD, structured for PDF export."""
    if not _is_configured():
        return {'error': 'Gemini API key not configured.'}

    prompt = f"""You are a professional resume writer. Create a polished, ATS-friendly resume tailored to the job description, preserving the candidate's real facts (names, employers, dates, education) but improving wording, structure, and keyword alignment.

Return ONLY a JSON object with this exact schema:
{{
  "name": "<candidate name from resume, or 'Candidate' if not found>",
  "contact": "<email | phone | location | linkedin (single line, use ' | ' separator)>",
  "summary": "<3-4 sentence professional summary tailored to the JD>",
  "skills": [<list of 10-20 relevant skills>],
  "experience": [
    {{"title": "<role>", "company": "<company>", "duration": "<dates>", "bullets": [<3-5 bullet strings>]}}
  ],
  "education": [
    {{"degree": "<degree>", "institution": "<school>", "year": "<year>"}}
  ],
  "projects": [
    {{"name": "<project>", "description": "<1-2 sentence description>"}}
  ],
  "certifications": [<list of strings, may be empty>]
}}

Candidate name hint: {candidate_name or 'extract from resume'}

ORIGINAL RESUME:
{resume_text[:7000]}

TARGET JOB DESCRIPTION:
{jd_text[:3000]}

Return ONLY the JSON. Do not invent employers or degrees that are not in the original."""

    try:
        response = _model().generate_content(prompt)
        data = _extract_json(response.text)
        if not data:
            return {'error': 'Could not parse rewrite response', 'raw': response.text[:500]}
        return data
    except Exception as e:
        return {'error': f'Gemini API error: {str(e)}'}
