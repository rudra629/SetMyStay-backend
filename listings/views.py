from rest_framework import viewsets, filters, permissions, parsers, generics, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from .serializers import StaffSerializer
from .models import Property, ListingImage, RoommateProfile, Amenity, Coupon, Advertisement # Import them
from .serializers import PropertySerializer, RoommateProfileSerializer, AmenitySerializer, CouponSerializer, AdvertisementSerializer

class PropertyViewSet(viewsets.ModelViewSet):
    ordering = ['-created_at']
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    serializer_class = PropertySerializer
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['city', 'property_type', 'bhk', 'furnishing']
    search_fields = ['title', 'area', 'description']
    ordering_fields = ['rent', 'created_at']

    def get_permissions(self):
        if self.action in ['destroy', 'update', 'partial_update']:
            return [permissions.IsAdminUser()] 
        return [permissions.IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        is_admin_view = self.request.query_params.get('admin') == 'true'
        if self.request.user.is_staff and is_admin_view:
            return Property.objects.all()
        return Property.objects.filter(status='APPROVED')

    # 👇 THIS IS THE MAGIC FUNCTION THAT SAVES AMENITIES AND IMAGES
    def perform_create(self, serializer):
        # 1. Save main data
        property_instance = serializer.save(owner=self.request.user)
        
        # 2. Save Images to Cloud/Local
        images = self.request.FILES.getlist('uploaded_images')
        for image in images:
            file_path = default_storage.save(f'property_images/{image.name}', ContentFile(image.read()))
            # 👇 CLOUD FIX: This automatically gets the S3 URL (or local URL if no S3 keys are set)
            full_image_url = default_storage.url(file_path)
            ListingImage.objects.create(property=property_instance, image_url=full_image_url, is_video=False)

        # 3. 👇 NEW: Catch and Save Video to Cloud 👇
        video_file = self.request.FILES.get('uploaded_video')
        if video_file:
            video_path = default_storage.save(f'property_videos/{video_file.name}', ContentFile(video_file.read()))
            full_video_url = default_storage.url(video_path)
            ListingImage.objects.create(property=property_instance, image_url=full_video_url, is_video=True)

        # 4. Save Amenities
        amenities_str = self.request.data.get('amenities_list', '')
        if amenities_str:
            amenity_names = [a.strip() for a in amenities_str.split(',') if a.strip()]
            for name in amenity_names:
                amenity_obj, created = Amenity.objects.get_or_create(name=name)
                property_instance.amenities.add(amenity_obj)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def toggle_favorite(self, request, pk=None):
        property_instance = self.get_object()
        user = request.user
        if user in property_instance.favorited_by.all():
            property_instance.favorited_by.remove(user)
            return Response({'status': 'removed', 'message': 'Removed from favorites'})
        else:
            property_instance.favorited_by.add(user)
            return Response({'status': 'added', 'message': 'Added to favorites'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def update_status(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'error': 'Only admins can update status'}, status=status.HTTP_403_FORBIDDEN)
            
        property_instance = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = ['APPROVED', 'REJECTED', 'PENDING']
        
        if new_status not in valid_statuses:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        property_instance.status = new_status
        property_instance.save()
        return Response({'status': 'success', 'message': f'Property {new_status.lower()} successfully'})
class RoommateViewSet(viewsets.ModelViewSet):
    ordering = ['-id']
    queryset = RoommateProfile.objects.filter(status='APPROVED')
    serializer_class = RoommateProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['location_preference', 'is_smoker', 'has_pets']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AmenityViewSet(viewsets.ModelViewSet):
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer


class RoommateListView(generics.ListAPIView):
    serializer_class = PropertySerializer
    
    def get_queryset(self):
        return Property.objects.filter(property_type='ROOMMATE', status='APPROVED')


# 👇 READY FOR NEXT FEATURE: My Listings Page
class MyPropertiesView(generics.ListAPIView):
    serializer_class = PropertySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user).order_by('-created_at')
    
class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all().order_by('-created_at')
    serializer_class = CouponSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

class AdvertisementViewSet(viewsets.ModelViewSet):
    queryset = Advertisement.objects.all().order_by('-created_at')
    serializer_class = AdvertisementSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
class StaffViewSet(viewsets.ModelViewSet):
    # Only fetch users who are marked as staff
    queryset = User.objects.filter(is_staff=True, is_superuser=False).order_by('-date_joined')
    # queryset = User.objects.filter(is_staff=True).order_by('-date_joined')
    serializer_class = StaffSerializer
    permission_classes = [permissions.IsAdminUser] # Strictly Admins only!