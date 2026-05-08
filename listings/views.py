from rest_framework import viewsets, filters, permissions, parsers
from django_filters.rest_framework import DjangoFilterBackend
from .models import Property, ListingImage, RoommateProfile, Amenity # Ensure ListingImage is imported
from .serializers import PropertySerializer, RoommateProfileSerializer, AmenitySerializer
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework import generics
from rest_framework.decorators import action
from rest_framework.response import Response

class PropertyViewSet(viewsets.ModelViewSet):
    ordering = ['-created_at']
    # 1. Allow anyone to VIEW, but only logged-in users to CREATE/EDIT
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    # 2. Allow parsing of File Uploads (Images/Videos)
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    queryset = Property.objects.filter(status='APPROVED')
    serializer_class = PropertySerializer
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['city', 'property_type', 'bhk', 'furnishing']
    search_fields = ['title', 'area', 'description']
    ordering_fields = ['rent', 'created_at']

    def get_queryset(self):
        # Staff sees everything, Public sees only 'APPROVED'
        if self.request.user.is_staff:
            return Property.objects.all()
        return Property.objects.filter(status='APPROVED')

    # 👇 THIS IS THE FIX!
    def perform_create(self, serializer):
        # 1. Save the Property first
        property_instance = serializer.save(owner=self.request.user)
        
        # 2. Handle the Images
        # We look for 'uploaded_images' which we packed in the Frontend FormData
        images = self.request.FILES.getlist('uploaded_images')
        
        for image in images:
            # A. Save file to "media/property_images/" folder
            file_path = default_storage.save(f'property_images/{image.name}', ContentFile(image.read()))
            
            # B. Generate the full URL (http://127.0.0.1:8000/media/...)
            full_image_url = f"{self.request.scheme}://{self.request.get_host()}/media/{file_path}"
            
            # C. Create the Database Record linking Image -> Property
            ListingImage.objects.create(property=property_instance, image_url=full_image_url)
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
class RoommateViewSet(viewsets.ModelViewSet):

    ordering = ['-id']
    queryset = RoommateProfile.objects.filter(status='APPROVED')
    serializer_class = RoommateProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # 👈 Added security
    
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
        # Only return approved ROOMMATE properties
        return Property.objects.filter(property_type='ROOMMATE', status='APPROVED')