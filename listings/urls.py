from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import CreateRazorpayOrderView, RazorpayWebhookView
router = DefaultRouter()
router.register(r'properties', views.PropertyViewSet, basename='property')
router.register(r'roommates', views.RoommateViewSet, basename='roommate')
router.register(r'amenities', views.AmenityViewSet, basename='amenity')
router.register(r'staff', views.StaffViewSet, basename='staff')
# 👇 ADD THESE TWO NEW LINES 👇
router.register(r'coupons', views.CouponViewSet, basename='coupon')
router.register(r'advertisements', views.AdvertisementViewSet, basename='advertisement')


urlpatterns = [
    path('', include(router.urls)),
    path('my-properties/', views.MyPropertiesView.as_view(), name='my-properties'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('payments/create-order/', CreateRazorpayOrderView.as_view(), name='create-order'),
    path('payments/webhook/', RazorpayWebhookView.as_view(), name='razorpay-webhook'),
    path('payments/my-history/', views.MyPurchasesView.as_view(), name='my-purchases'),
    path('payments/all-history/', views.AllPurchasesAdminView.as_view(), name='all-purchases'),
]