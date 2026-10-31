from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('listings.urls')),
    path('api/users/', include('users.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# --- AUTO-SEED ADMIN USER & COUPONS ON RENDER STARTUP ---
from django.contrib.auth import get_user_model

try:
    User = get_user_model()
    for uname, pwd in [('admin', 'Admin@12345'), ('rohan', 'Admin@12345')]:
        u, _ = User.objects.get_or_create(
            username=uname,
            defaults={
                'email': f'{uname}@setmystay.com',
                'first_name': uname.capitalize(),
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        u.is_staff = True
        u.is_superuser = True
        u.is_active = True
        u.set_password(pwd)
        u.save()

    from listings.models import Coupon
    Coupon.objects.get_or_create(code='WELCOME10', defaults={'discount_percentage': 10, 'is_active': True})
    Coupon.objects.get_or_create(code='STAY20', defaults={'discount_percentage': 20, 'is_active': True})
except Exception as e:
    print("Startup seed note:", e)