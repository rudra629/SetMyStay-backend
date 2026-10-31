from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from .views import (
    CreateRazorpayOrderView,
    RazorpayWebhookView,
    VerifyLocalPaymentView,
    MyPropertiesView,
    MyPurchasesView,
    AllPurchasesAdminView,
)

router = DefaultRouter()
router.register(r'properties', views.PropertyViewSet, basename='property')
router.register(r'roommates', views.RoommateViewSet, basename='roommate')
router.register(r'amenities', views.AmenityViewSet, basename='amenity')
router.register(r'staff', views.StaffViewSet, basename='staff')
router.register(r'coupons', views.CouponViewSet, basename='coupon')
router.register(r'advertisements', views.AdvertisementViewSet, basename='advertisement')

urlpatterns = [
    path('', include(router.urls)),
    path('my-properties/', MyPropertiesView.as_view(), name='my-properties'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('payments/create-order/', CreateRazorpayOrderView.as_view(), name='create-order'),
    path('payments/webhook/', RazorpayWebhookView.as_view(), name='razorpay-webhook'),
    path('payments/my-history/', MyPurchasesView.as_view(), name='my-purchases'),
    path('payments/all-history/', AllPurchasesAdminView.as_view(), name='all-purchases'),
    path('payments/verify-local/', VerifyLocalPaymentView.as_view(), name='verify-local'),
]