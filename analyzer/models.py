from django.db import models
from django.conf import settings


class Resume(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resumes')
    file = models.FileField(upload_to='resumes/')
    original_filename = models.CharField(max_length=255)
    extracted_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.original_filename}"


class JobDescription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='job_descriptions')
    title = models.CharField(max_length=255, blank=True)
    text = models.TextField()
    file = models.FileField(upload_to='job_descriptions/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title or 'JD'}"


class MatchResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='match_results')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='match_results')
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE, related_name='match_results')
    match_score = models.FloatField()
    matched_skills = models.JSONField(default=list)
    missing_skills = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    shap_explanation = models.JSONField(default=dict)
    # Advanced analysis fields
    score_breakdown = models.JSONField(default=dict)
    semantic_scores = models.JSONField(default=dict)
    section_scores = models.JSONField(default=dict)
    keyword_analysis = models.JSONField(default=dict)
    experience_analysis = models.JSONField(default=dict)
    matched_by_group = models.JSONField(default=dict)
    missing_by_group = models.JSONField(default=dict)
    critical_missing = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.match_score:.1f}%"
