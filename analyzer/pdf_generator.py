"""Generate styled PDF resumes from structured data using ReportLab."""
import io

from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem,
)


def _styles():
    base = getSampleStyleSheet()
    return {
        'name': ParagraphStyle('Name', parent=base['Title'], fontSize=22, alignment=TA_CENTER,
                               textColor=colors.HexColor('#1a1a2e'), spaceAfter=4),
        'contact': ParagraphStyle('Contact', parent=base['Normal'], fontSize=10, alignment=TA_CENTER,
                                  textColor=colors.HexColor('#555'), spaceAfter=10),
        'section': ParagraphStyle('Section', parent=base['Heading2'], fontSize=13,
                                  textColor=colors.HexColor('#1a1a2e'), spaceBefore=12, spaceAfter=4,
                                  fontName='Helvetica-Bold'),
        'role': ParagraphStyle('Role', parent=base['Normal'], fontSize=11, fontName='Helvetica-Bold',
                               textColor=colors.HexColor('#222'), spaceAfter=2),
        'meta': ParagraphStyle('Meta', parent=base['Normal'], fontSize=10, textColor=colors.HexColor('#666'),
                               spaceAfter=4, fontName='Helvetica-Oblique'),
        'body': ParagraphStyle('Body', parent=base['Normal'], fontSize=10, leading=14,
                               alignment=TA_LEFT, textColor=colors.HexColor('#222')),
        'bullet': ParagraphStyle('Bullet', parent=base['Normal'], fontSize=10, leading=13,
                                 leftIndent=12, textColor=colors.HexColor('#222')),
    }


def _hr():
    return HRFlowable(width='100%', thickness=0.7, color=colors.HexColor('#cccccc'),
                      spaceBefore=2, spaceAfter=6)


def _safe(s):
    if s is None:
        return ''
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def build_resume_pdf(data: dict) -> bytes:
    """Render a structured resume dict (from generate_full_rewritten_resume) into PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                            title=f"Resume - {data.get('name', 'Candidate')}")
    s = _styles()
    story = []

    story.append(Paragraph(_safe(data.get('name', 'Candidate')), s['name']))
    contact = data.get('contact', '')
    if contact:
        story.append(Paragraph(_safe(contact), s['contact']))
    story.append(_hr())

    summary = data.get('summary', '')
    if summary:
        story.append(Paragraph('PROFESSIONAL SUMMARY', s['section']))
        story.append(Paragraph(_safe(summary), s['body']))

    skills = data.get('skills', [])
    if skills:
        story.append(Paragraph('SKILLS', s['section']))
        skills_text = ' • '.join(_safe(sk) for sk in skills if sk)
        story.append(Paragraph(skills_text, s['body']))

    experience = data.get('experience', [])
    if experience:
        story.append(Paragraph('EXPERIENCE', s['section']))
        for exp in experience:
            title = _safe(exp.get('title', ''))
            company = _safe(exp.get('company', ''))
            duration = _safe(exp.get('duration', ''))
            header = f"{title} — {company}" if company else title
            story.append(Paragraph(header, s['role']))
            if duration:
                story.append(Paragraph(duration, s['meta']))
            bullets = exp.get('bullets', []) or []
            if bullets:
                items = [ListItem(Paragraph(_safe(b), s['bullet']), leftIndent=10) for b in bullets if b]
                story.append(ListFlowable(items, bulletType='bullet', start='•', leftIndent=14))
            story.append(Spacer(1, 4))

    projects = data.get('projects', [])
    if projects:
        story.append(Paragraph('PROJECTS', s['section']))
        for p in projects:
            name = _safe(p.get('name', ''))
            desc = _safe(p.get('description', ''))
            story.append(Paragraph(f"<b>{name}</b> — {desc}", s['body']))
            story.append(Spacer(1, 3))

    education = data.get('education', [])
    if education:
        story.append(Paragraph('EDUCATION', s['section']))
        for ed in education:
            degree = _safe(ed.get('degree', ''))
            inst = _safe(ed.get('institution', ''))
            year = _safe(ed.get('year', ''))
            line = f"<b>{degree}</b>, {inst}" if inst else f"<b>{degree}</b>"
            if year:
                line += f"  <font color='#666'>({year})</font>"
            story.append(Paragraph(line, s['body']))
            story.append(Spacer(1, 2))

    certs = data.get('certifications', [])
    if certs:
        story.append(Paragraph('CERTIFICATIONS', s['section']))
        items = [ListItem(Paragraph(_safe(c), s['bullet']), leftIndent=10) for c in certs if c]
        story.append(ListFlowable(items, bulletType='bullet', start='•', leftIndent=14))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


def build_analysis_report_pdf(result, ai_data: dict | None = None) -> bytes:
    """Render an analysis report (score, skills, recommendations) as PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                            title="Resume Analysis Report")
    s = _styles()
    story = []

    story.append(Paragraph('Resume Analysis Report', s['name']))
    story.append(Paragraph(
        f"Resume: {_safe(result.resume.original_filename)} &nbsp;|&nbsp; "
        f"JD: {_safe(result.job_description.title or 'Untitled')}",
        s['contact']))
    story.append(_hr())

    story.append(Paragraph('OVERALL MATCH SCORE', s['section']))
    story.append(Paragraph(f"<b>{result.match_score:.1f}%</b>", s['body']))

    if ai_data and not ai_data.get('error'):
        story.append(Paragraph('AI ASSESSMENT', s['section']))
        story.append(Paragraph(
            f"AI Score: <b>{ai_data.get('ai_score', '—')}/100</b> &nbsp;•&nbsp; "
            f"Match: <b>{ai_data.get('match_percentage', '—')}%</b>", s['body']))
        if ai_data.get('summary_feedback'):
            story.append(Spacer(1, 4))
            story.append(Paragraph(_safe(ai_data['summary_feedback']), s['body']))

        if ai_data.get('strengths'):
            story.append(Paragraph('STRENGTHS', s['section']))
            items = [ListItem(Paragraph(_safe(x), s['bullet']), leftIndent=10) for x in ai_data['strengths']]
            story.append(ListFlowable(items, bulletType='bullet', start='•', leftIndent=14))

        if ai_data.get('weaknesses'):
            story.append(Paragraph('WEAKNESSES', s['section']))
            items = [ListItem(Paragraph(_safe(x), s['bullet']), leftIndent=10) for x in ai_data['weaknesses']]
            story.append(ListFlowable(items, bulletType='bullet', start='•', leftIndent=14))

    if result.matched_skills:
        story.append(Paragraph('MATCHED SKILLS', s['section']))
        story.append(Paragraph(' • '.join(_safe(x) for x in result.matched_skills), s['body']))

    if result.missing_skills:
        story.append(Paragraph('MISSING SKILLS', s['section']))
        story.append(Paragraph(' • '.join(_safe(x) for x in result.missing_skills), s['body']))

    suggestions = (ai_data or {}).get('improvement_suggestions') or result.recommendations or []
    if suggestions:
        story.append(Paragraph('IMPROVEMENT SUGGESTIONS', s['section']))
        items = []
        for sug in suggestions:
            text = sug if isinstance(sug, str) else (sug.get('text') or sug.get('title') or str(sug))
            items.append(ListItem(Paragraph(_safe(text), s['bullet']), leftIndent=10))
        story.append(ListFlowable(items, bulletType='1', leftIndent=14))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
