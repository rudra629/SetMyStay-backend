from datetime import timedelta
import razorpay
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, permissions, parsers, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Property,
    ListingImage,
    RoommateProfile,
    Amenity,
    Coupon,
    Advertisement,
    Purchase,
)
from .serializers import (
    PropertySerializer,
    RoommateProfileSerializer,
    AmenitySerializer,
    CouponSerializer,
    AdvertisementSerializer,
    PurchaseSerializer,
    StaffSerializer,
)


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


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
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        # Always allow detail actions (update_status, destroy, retrieve, toggle_favorite) to find PENDING properties
        if self.action in ['update_status', 'destroy', 'retrieve', 'update', 'partial_update', 'toggle_favorite']:
            return Property.objects.all().order_by('-created_at')

        is_admin_view = self.request.query_params.get('admin') == 'true'
        if is_admin_view:
            return Property.objects.all().order_by('-created_at')

        return Property.objects.filter(status='APPROVED').order_by('-created_at')

    def perform_create(self, serializer):
        # 1. Save main property data and force status='PENDING' so it immediately shows in Admin Dashboard
        owner = self.request.user if self.request.user.is_authenticated else User.objects.first()
        property_instance = serializer.save(owner=owner, status='PENDING')

        # 2. Save Images to Cloud/Local
        images = self.request.FILES.getlist('uploaded_images')
        for image in images:
            file_path = default_storage.save(f'property_images/{image.name}', ContentFile(image.read()))
            full_image_url = default_storage.url(file_path)
            ListingImage.objects.create(property=property_instance, image_url=full_image_url, is_video=False)

        # 3. Save Video to Cloud/Local if provided
        video_file = self.request.FILES.get('uploaded_video')
        if video_file:
            video_path = default_storage.save(f'property_videos/{video_file.name}', ContentFile(video_file.read()))
            full_video_url = default_storage.url(video_path)
            ListingImage.objects.create(property=property_instance, image_url=full_video_url, is_video=True)

        # 4. Save Amenities
        amenities_str = self.request.data.get('amenities_list', '')
        if amenities_str:
            if isinstance(amenities_str, list):
                amenities_str = ','.join(amenities_str)
            amenity_names = [a.replace('[', '').replace(']', '').replace('"', '').strip() for a in str(amenities_str).split(',') if a.strip()]
            for name in amenity_names:
                if name:
                    amenity_obj, _ = Amenity.objects.get_or_create(name=name)
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

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def update_status(self, request, pk=None):
        property_instance = Property.objects.filter(pk=pk).first()
        if not property_instance:
            return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)

        new_status = str(request.data.get('status', '')).upper()
        valid_statuses = ['APPROVED', 'REJECTED', 'PENDING']

        if new_status not in valid_statuses:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

        property_instance.status = new_status

        if new_status in ['APPROVED', 'REJECTED']:
            if request.user and request.user.is_authenticated:
                property_instance.reviewed_by = request.user
            property_instance.reviewed_at = timezone.now()
        else:
            property_instance.reviewed_by = None
            property_instance.reviewed_at = None

        property_instance.save()
        return Response({'status': 'success', 'message': f'Property {new_status.lower()} successfully'})


class RoommateViewSet(viewsets.ModelViewSet):
    ordering = ['-id']
    serializer_class = RoommateProfileSerializer
    permission_classes = [permissions.AllowAny]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['location_preference', 'is_smoker', 'has_pets']

    def get_queryset(self):
        if self.action in ['update_status', 'destroy', 'retrieve', 'update', 'partial_update']:
            return RoommateProfile.objects.all().order_by('-id')
        is_admin_view = self.request.query_params.get('admin') == 'true'
        if is_admin_view:
            return RoommateProfile.objects.all().order_by('-id')
        return RoommateProfile.objects.all().order_by('-id')

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else User.objects.first()
        serializer.save(user=user, status='PENDING')

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def update_status(self, request, pk=None):
        profile = RoommateProfile.objects.filter(pk=pk).first()
        if not profile:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

        new_status = str(request.data.get('status', '')).upper()
        if new_status in ['APPROVED', 'REJECTED']:
            if request.user and request.user.is_authenticated:
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
    permission_classes = [permissions.AllowAny]


class RoommateListView(generics.ListAPIView):
    serializer_class = PropertySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Property.objects.filter(property_type='ROOMMATE', status='APPROVED')


class MyPropertiesView(generics.ListAPIView):
    serializer_class = PropertySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user).order_by('-created_at')


class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all().order_by('-created_at')
    serializer_class = CouponSerializer
    permission_classes = [permissions.AllowAny]


class AdvertisementViewSet(viewsets.ModelViewSet):
    queryset = Advertisement.objects.all().order_by('-created_at')
    serializer_class = AdvertisementSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    permission_classes = [permissions.AllowAny]


class StaffViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_staff=True, is_superuser=False).order_by('-date_joined')
    serializer_class = StaffSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = []

        for staff in queryset:
            prop_reviews = Property.objects.filter(reviewed_by=staff).exclude(reviewed_at__isnull=True)
            room_reviews = RoommateProfile.objects.filter(reviewed_by=staff).exclude(reviewed_at__isnull=True)

            approved_count = prop_reviews.filter(status='APPROVED').count() + room_reviews.filter(status='APPROVED').count()
            rejected_count = prop_reviews.filter(status='REJECTED').count() + room_reviews.filter(status='REJECTED').count()

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

            serializer = self.get_serializer(staff)
            staff_data = serializer.data
            staff_data['approved_count'] = approved_count
            staff_data['rejected_count'] = rejected_count
            staff_data['avg_processing_hours'] = avg_hours

            data.append(staff_data)

        return Response(data)


class CreateRazorpayOrderView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        amount = request.data.get("amount")
        property_id = request.data.get("property_id")
        plan_name = request.data.get("plan_name", "Listing Fee")

        if not amount:
            return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = get_razorpay_client()
            user_id_str = str(request.user.id) if (request.user and request.user.is_authenticated) else ""
            order_data = {
                "amount": int(float(amount) * 100),
                "currency": "INR",
                "payment_capture": "1",
                "notes": {
                    "property_id": str(property_id) if property_id else "",
                    "user_id": user_id_str,
                    "plan_name": str(plan_name),
                }
            }
            razorpay_order = client.order.create(data=order_data)

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
            client = get_razorpay_client()
            client.utility.verify_webhook_signature(
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

                if property_id:
                    prop = Property.objects.filter(id=property_id).first()
                    if prop:
                        prop.status = 'PENDING'
                        prop.save()

                if user_id:
                    user = User.objects.filter(id=user_id).first()
                    if user:
                        Purchase.objects.get_or_create(
                            razorpay_payment_id=payment_entity.get('id'),
                            defaults={
                                'user': user,
                                'plan_name': plan_name,
                                'amount': amount,
                                'status': 'SUCCESS',
                            }
                        )

            return Response({"status": "success"}, status=status.HTTP_200_OK)

        except Exception:
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)


class VerifyLocalPaymentView(APIView):
    """
    Handles verification right after Razorpay modal succeeds on the frontend.
    Works for BOTH:
    1) Property Listing Fee (updates property status to PENDING so Admin sees it)
    2) Subscription / Unlock Plans (where property_id is None)
    And records the Purchase in the database so Purchase History works!
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        property_id = request.data.get('property_id')
        payment_id = request.data.get('razorpay_payment_id') or f"pay_{int(timezone.now().timestamp())}"
        plan_name = request.data.get('plan_name') or ('Property Listing Fee' if property_id else 'Subscription Plan')
        amount = request.data.get('amount') or 499

        # 1. If property_id is provided, mark that property as PENDING for Admin approval
        if property_id:
            prop = Property.objects.filter(id=property_id).first()
            if prop:
                prop.status = 'PENDING'
                prop.save()
        else:
            # Fallback: if the user just created a property seconds ago and property_id wasn't passed,
            # ensure their latest property is set to PENDING
            if request.user and request.user.is_authenticated and 'listing' in str(plan_name).lower():
                latest_prop = Property.objects.filter(owner=request.user).order_by('-created_at').first()
                if latest_prop and latest_prop.status not in ['APPROVED', 'REJECTED']:
                    latest_prop.status = 'PENDING'
                    latest_prop.save()

        # 2. Save the Purchase record so it shows up in User & Admin Purchase History
        try:
            user = request.user if (request.user and request.user.is_authenticated) else User.objects.first()
            if user:
                Purchase.objects.get_or_create(
                    razorpay_payment_id=payment_id,
                    defaults={
                        'user': user,
                        'plan_name': plan_name,
                        'amount': amount,
                        'status': 'SUCCESS',
                    }
                )
        except Exception as e:
            print("Purchase save note:", e)

        return Response({
            'status': 'success',
            'message': 'Payment verified and recorded successfully'
        }, status=status.HTTP_200_OK)


class MyPurchasesView(generics.ListAPIView):
    serializer_class = PurchaseSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        if self.request.user and self.request.user.is_authenticated:
            return Purchase.objects.filter(user=self.request.user).order_by('-created_at')
        return Purchase.objects.all().order_by('-created_at')[:10]


class AllPurchasesAdminView(generics.ListAPIView):
    serializer_class = PurchaseSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Purchase.objects.all().order_by('-created_at')