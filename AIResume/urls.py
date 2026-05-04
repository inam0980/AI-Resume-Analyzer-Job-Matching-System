from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('analyzer/', include('analyzer.urls')),
    path('', lambda request: redirect('analyzer:upload'), name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
