import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .forms import ResumeUploadForm, JobDescriptionForm
from .models import Resume, JobDescription, MatchResult
from .extractor import extract_text
from .matcher import compute_match
from .explainer import build_shap_explanation, generate_recommendations


@login_required
def upload_view(request):
    return render(request, 'analyzer/upload.html', {
        'resume_form': ResumeUploadForm(),
        'jd_form':     JobDescriptionForm(),
    })


@login_required
@require_POST
def analyze_view(request):
    resume_form = ResumeUploadForm(request.POST, request.FILES)
    jd_form     = JobDescriptionForm(request.POST, request.FILES)

    if not resume_form.is_valid() or not jd_form.is_valid():
        errors = {**resume_form.errors, **jd_form.errors}
        return JsonResponse({'error': 'Invalid form data', 'details': str(errors)}, status=400)

    # ── Save resume ──
    resume_obj = resume_form.save(commit=False)
    resume_obj.user = request.user
    file = request.FILES['file']
    resume_obj.original_filename = file.name
    resume_obj.extracted_text = extract_text(file, file.name)
    resume_obj.save()

    if not resume_obj.extracted_text.strip():
        return JsonResponse({'error': 'Could not extract text from resume. Please use a text-based PDF or DOCX.'}, status=400)

    # ── Save JD ──
    jd_obj = jd_form.save(commit=False)
    jd_obj.user = request.user
    if 'jd_file' in request.FILES:
        jd_file = request.FILES['jd_file']
        jd_obj.text = extract_text(jd_file, jd_file.name)
    if not jd_obj.text.strip():
        return JsonResponse({'error': 'Job description text is empty.'}, status=400)
    jd_obj.save()

    # ── Advanced analysis ──
    match_data = compute_match(resume_obj.extracted_text, jd_obj.text)

    shap_data = build_shap_explanation(
        resume_obj.extracted_text,
        jd_obj.text,
        match_data['matched_skills'],
        match_data['missing_skills'],
    )

    recommendations = generate_recommendations(
        matched_skills    = match_data['matched_skills'],
        missing_skills    = match_data['missing_skills'],
        match_score       = match_data['match_score'],
        critical_missing  = match_data['critical_missing'],
        keyword_analysis  = match_data['keyword_analysis'],
        section_scores    = match_data['section_scores'],
        experience        = match_data['experience'],
    )

    # ── Persist ──
    result = MatchResult.objects.create(
        user                = request.user,
        resume              = resume_obj,
        job_description     = jd_obj,
        match_score         = match_data['match_score'],
        matched_skills      = match_data['matched_skills'],
        missing_skills      = match_data['missing_skills'],
        recommendations     = recommendations,
        shap_explanation    = shap_data,
        score_breakdown     = match_data['score_breakdown'],
        semantic_scores     = match_data['semantic'],
        section_scores      = match_data['section_scores'],
        keyword_analysis    = match_data['keyword_analysis'],
        experience_analysis = match_data['experience'],
        matched_by_group    = match_data['matched_by_group'],
        missing_by_group    = match_data['missing_by_group'],
        critical_missing    = match_data['critical_missing'],
    )

    return JsonResponse({'redirect': f'/analyzer/results/{result.pk}/'})


@login_required
def results_view(request, pk):
    result = get_object_or_404(MatchResult, pk=pk, user=request.user)
    return render(request, 'analyzer/results.html', {'result': result})


@login_required
def history_view(request):
    results = MatchResult.objects.filter(user=request.user).select_related('resume', 'job_description')
    return render(request, 'analyzer/history.html', {'results': results})


@login_required
def result_detail_api(request, pk):
    result = get_object_or_404(MatchResult, pk=pk, user=request.user)
    return JsonResponse({
        'id':                   result.pk,
        'match_score':          result.match_score,
        'matched_skills':       result.matched_skills,
        'missing_skills':       result.missing_skills,
        'recommendations':      result.recommendations,
        'shap_explanation':     result.shap_explanation,
        'score_breakdown':      result.score_breakdown,
        'semantic_scores':      result.semantic_scores,
        'section_scores':       result.section_scores,
        'keyword_analysis':     result.keyword_analysis,
        'experience_analysis':  result.experience_analysis,
        'matched_by_group':     result.matched_by_group,
        'missing_by_group':     result.missing_by_group,
        'critical_missing':     result.critical_missing,
        'resume_filename':      result.resume.original_filename,
        'jd_title':             result.job_description.title,
        'created_at':           result.created_at.isoformat(),
    })
