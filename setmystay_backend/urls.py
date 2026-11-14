import os
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('api/', include('listings.urls')),
    path('api/users/', include('users.urls')),
]

# The Django admin site (/admin/) only asks for a password, so it would skip the
# email code. It is off unless DJANGO_ADMIN_SITE_ENABLED=True is set on Render.
if os.environ.get('DJANGO_ADMIN_SITE_ENABLED') == 'True':
    urlpatterns.insert(0, path('admin/', admin.site.urls))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# --- FIRST-RUN SEED ---
# Creates the admin account ONLY if it does not exist yet, and never resets an
# existing password (before, every restart reset it to a default value).
from django.contrib.auth import get_user_model

try:
    User = get_user_model()
    admin_uname = os.environ.get('DJANGO_ADMIN_USERNAME', 'admin')
    admin_pwd = os.environ.get('DJANGO_ADMIN_PASSWORD')
    if admin_pwd and not User.objects.filter(username=admin_uname).exists():
        User.objects.create_superuser(
            username=admin_uname,
            email=os.environ.get('DJANGO_ADMIN_EMAIL', ''),
            password=admin_pwd,
        )

    from listings.models import Coupon
    if not Coupon.objects.exists():
        Coupon.objects.get_or_create(code='WELCOME10', defaults={'discount_percentage': 10, 'is_active': True})
        Coupon.objects.get_or_create(code='STAY20', defaults={'discount_percentage': 20, 'is_active': True})
except Exception as e:
    print("Startup seed note:", e)
