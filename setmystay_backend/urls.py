from django.contrib import admin
from django.urls import path, include
from django.conf import settings # 👈 Import settings
from django.conf.urls.static import static # 👈 Import static
from . import views
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('listings.urls')),
    path('api/auth/', include('users.urls')),
    path('api/users/', include('users.urls')),
    path('api/', include('management.urls')),
    path('payments/verify-local/', views.verify_local_payment, name='verify_local_payment'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# REMOVE THE BLOCK DURING FINAL PRODUCTION
from django.contrib.auth import get_user_model

User = get_user_model()
try:
    # Checks if an admin account already exists to prevent errors
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@setmystay.com', 'Admin@12345')
        print("Superuser created automatically!")
except Exception as e:
    pass