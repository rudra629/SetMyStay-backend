from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropertyViewSet, RoommateViewSet, AmenityViewSet

router = DefaultRouter()
router.register(r'properties', PropertyViewSet)
router.register(r'roommates', RoommateViewSet)
router.register(r'amenities', AmenityViewSet)

urlpatterns = [
    path('', include(router.urls)),
]