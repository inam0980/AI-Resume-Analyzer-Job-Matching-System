from django.urls import path
from . import views

app_name = 'analyzer'

urlpatterns = [
    path('', views.upload_view, name='upload'),
    path('analyze/', views.analyze_view, name='analyze'),
    path('results/<int:pk>/', views.results_view, name='results'),
    path('history/', views.history_view, name='history'),
    path('api/result/<int:pk>/', views.result_detail_api, name='result_api'),
]
