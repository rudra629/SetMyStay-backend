# listings/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropertyViewSet, RoommateViewSet, AmenityViewSet, RoommateListView

# This handles all the standard CRUD routes automatically
router = DefaultRouter()
router.register(r'properties', PropertyViewSet, basename='property')
router.register(r'roommate-profiles', RoommateViewSet, basename='roommate-profile')
router.register(r'amenities', AmenityViewSet, basename='amenity')

urlpatterns = [
    # The standard router paths (e.g., /api/listings/properties/)
    path('', include(router.urls)),
    
    # 👇 ADD THIS: Our custom path specifically for fetching Roommate Properties
    path('roommate-properties/', RoommateListView.as_view(), name='roommate-properties'),
]