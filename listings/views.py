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
from django.utils import timezone # 👈 Add this at the very top of views.py with your other imports
from datetime import timedelta    # 👈 Add this at the very top of views.py too
import razorpay
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

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

        if new_status in ['APPROVED', 'REJECTED']:
            property_instance.reviewed_by = request.user
            property_instance.reviewed_at = timezone.now()
        else:
            # If an admin moves it back to PENDING, clear the tracking
            property_instance.reviewed_by = None
            property_instance.reviewed_at = None

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

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def update_status(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'error': 'Only admins can update status'}, status=status.HTTP_403_FORBIDDEN)
            
        profile = self.get_object()
        new_status = request.data.get('status')
        
        if new_status in ['APPROVED', 'REJECTED']:
            profile.reviewed_by = request.user
            profile.reviewed_at = timezone.now()
        else:
            profile.reviewed_by = None
            profile.reviewed_at = None
            
        profile.status = new_status
        profile.save()
        return Response({'status': 'success', 'message': f'Profile {new_status.lower()} successfully'})

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
    queryset = User.objects.filter(is_staff=True, is_superuser=False).order_by('-date_joined')
    serializer_class = StaffSerializer
    permission_classes = [permissions.IsAdminUser]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = []

        for staff in queryset:
            # 1. Grab BOTH Property and Roommate reviews for this staff member
            prop_reviews = Property.objects.filter(reviewed_by=staff).exclude(reviewed_at__isnull=True)
            room_reviews = RoommateProfile.objects.filter(reviewed_by=staff).exclude(reviewed_at__isnull=True)
            
            # 2. Combine the counts
            approved_count = prop_reviews.filter(status='APPROVED').count() + room_reviews.filter(status='APPROVED').count()
            rejected_count = prop_reviews.filter(status='REJECTED').count() + room_reviews.filter(status='REJECTED').count()

            # 3. Calculate total time for both
            total_duration = timedelta(0)
            total_reviews = prop_reviews.count() + room_reviews.count()

            for r in prop_reviews:
                if r.reviewed_at and r.created_at:
                    total_duration += (r.reviewed_at - r.created_at)
            for r in room_reviews:
                if r.reviewed_at and r.created_at:
                    total_duration += (r.reviewed_at - r.created_at)

            avg_hours = "N/A"
            if total_reviews > 0:
                avg_td = total_duration / total_reviews
                avg_hours = round(avg_td.total_seconds() / 3600, 1)

            # 4. Package data for frontend
            serializer = self.get_serializer(staff)
            staff_data = serializer.data
            
            staff_data['approved_count'] = approved_count
            staff_data['rejected_count'] = rejected_count
            staff_data['avg_processing_hours'] = avg_hours

            data.append(staff_data)

        return Response(data)
# Initialize Razorpay Client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class CreateRazorpayOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        amount = request.data.get("amount") # Expected in INR
        property_id = request.data.get("property_id")
        
        if not amount:
            return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create Order in Razorpay (amount must be in paise)
            order_data = {
                "amount": int(float(amount) * 100), 
                "currency": "INR",
                "payment_capture": "1",
                "notes": {
                    "property_id": property_id,
                    "user_id": request.user.id
                }
            }
            razorpay_order = razorpay_client.order.create(data=order_data)
            
            return Response({
                "order_id": razorpay_order['id'],
                "amount": razorpay_order['amount'],
                "currency": razorpay_order['currency'],
                "razorpay_key": settings.RAZORPAY_KEY_ID
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RazorpayWebhookView(APIView):
    permission_classes = [permissions.AllowAny] # Webhooks come from Razorpay, not logged-in users

    def post(self, request):
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        payload = request.body.decode('utf-8')
        
        try:
            # Verify the signature to ensure it's actually from Razorpay
            razorpay_client.utility.verify_webhook_signature(
                payload, 
                webhook_signature, 
                settings.RAZORPAY_WEBHOOK_SECRET
            )
            
            event_type = request.data.get('event')
            if event_type == 'payment.captured':
                payment_entity = request.data['payload']['payment']['entity']
                property_id = payment_entity.get('notes', {}).get('property_id')
                
                # Update the property status to indicate payment is complete
                if property_id:
                    from .models import Property
                    prop = Property.objects.filter(id=property_id).first()
                    if prop:
                        prop.status = 'APPROVED' # Or however you track paid properties
                        prop.save()

            return Response({"status": "success"}, status=status.HTTP_200_OK)
            
        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

from .models import Purchase
from .serializers import PurchaseSerializer

class CreateRazorpayOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        amount = request.data.get("amount") 
        property_id = request.data.get("property_id")
        plan_name = request.data.get("plan_name", "Listing Fee") # 👈 Added plan name
        
        if not amount:
            return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order_data = {
                "amount": int(float(amount) * 100), 
                "currency": "INR",
                "payment_capture": "1",
                "notes": {
                    "property_id": property_id if property_id else "",
                    "user_id": str(request.user.id),
                    "plan_name": plan_name # 👈 Send plan name to Razorpay
                }
            }
            razorpay_order = razorpay_client.order.create(data=order_data)
            
            return Response({
                "order_id": razorpay_order['id'],
                "amount": razorpay_order['amount'],
                "currency": razorpay_order['currency'],
                "razorpay_key": settings.RAZORPAY_KEY_ID
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RazorpayWebhookView(APIView):
    permission_classes = [permissions.AllowAny] 

    def post(self, request):
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        payload = request.body.decode('utf-8')
        
        try:
            razorpay_client.utility.verify_webhook_signature(
                payload, 
                webhook_signature, 
                settings.RAZORPAY_WEBHOOK_SECRET
            )
            
            event_type = request.data.get('event')
            if event_type == 'payment.captured':
                payment_entity = request.data['payload']['payment']['entity']
                notes = payment_entity.get('notes', {})
                property_id = notes.get('property_id')
                user_id = notes.get('user_id')
                plan_name = notes.get('plan_name', 'Standard Plan')
                amount = payment_entity.get('amount', 0) / 100
                
                # 1. Update Property Status (if it's a listing fee)
                if property_id:
                    from .models import Property
                    prop = Property.objects.filter(id=property_id).first()
                    if prop:
                        prop.status = 'APPROVED'
                        prop.save()

                # 2. Record the Purchase in History 👇
                if user_id:
                    user = User.objects.filter(id=user_id).first()
                    if user:
                        Purchase.objects.create(
                            user=user,
                            plan_name=plan_name,
                            amount=amount,
                            razorpay_payment_id=payment_entity.get('id'),
                            status='SUCCESS'
                        )

            return Response({"status": "success"}, status=status.HTTP_200_OK)
            
        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

# 👇 New API Views for History 👇
class MyPurchasesView(generics.ListAPIView):
    serializer_class = PurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Purchase.objects.filter(user=self.request.user).order_by('-created_at')

class AllPurchasesAdminView(generics.ListAPIView):
    serializer_class = PurchaseSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Purchase.objects.all().order_by('-created_at')