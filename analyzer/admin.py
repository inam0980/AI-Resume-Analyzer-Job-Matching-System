from django.contrib import admin
from .models import Resume, JobDescription, MatchResult


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('user', 'original_filename', 'uploaded_at')
    search_fields = ('user__username', 'original_filename')


@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'created_at')
    search_fields = ('user__username', 'title')


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'match_score', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username',)
