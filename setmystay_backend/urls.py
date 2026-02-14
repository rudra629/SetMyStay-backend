from django.contrib import admin
from django.urls import path, include
from django.conf import settings # 👈 Import settings
from django.conf.urls.static import static # 👈 Import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('listings.urls')),
    path('api/auth/', include('users.urls')),
]

# 👇 This allows the browser to load images from your computer
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)