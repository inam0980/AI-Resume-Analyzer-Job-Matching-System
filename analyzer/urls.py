from django.urls import path
from . import views

app_name = 'analyzer'

urlpatterns = [
    path('', views.upload_view, name='upload'),
    path('analyze/', views.analyze_view, name='analyze'),
    path('results/<int:pk>/', views.results_view, name='results'),
    path('history/', views.history_view, name='history'),
    path('api/result/<int:pk>/', views.result_detail_api, name='result_api'),
    path('ai/analyze/<int:pk>/', views.ai_analyze_view, name='ai_analyze'),
    path('ai/rewrite/<int:pk>/', views.ai_rewrite_view, name='ai_rewrite'),
    path('export/resume/<int:pk>/', views.export_resume_pdf, name='export_resume'),
    path('export/report/<int:pk>/', views.export_report_pdf, name='export_report'),
]
