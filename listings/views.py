from datetime import datetime, time as dt_time, timedelta
from zoneinfo import ZoneInfo
import razorpay
import cloudinary
import cloudinary.uploader
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
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
    PricingConfig,
    UserUnlock,
    SwipeUsage,
)
from .permissions import (
    IsStaffOrAdmin, IsSuperAdmin, ReadOnlyOrSuperAdmin, ReadOnlyOrStaff, IsOwnerOrStaff, is_staff_user,
)
from .entitlements import get_entitlement, pricing_key_for_plan
from .serializers import (
    PropertySerializer,
    RoommateProfileSerializer,
    AmenitySerializer,
    CouponSerializer,
    AdvertisementSerializer,
    PurchaseSerializer,
    StaffSerializer,
)


def minimum_plan_price(plan_name):
    """Lowest valid price for an unlock plan: admin price minus the best active coupon."""
    key = pricing_key_for_plan(plan_name)
    cfg = PricingConfig.objects.filter(key='global_pricing').first()
    prices = (cfg.pricing_data if cfg and cfg.pricing_data else DEFAULT_PRICING).get('unlocks', {})
    full_price = float(prices.get(key) or DEFAULT_PRICING['unlocks'][key])
    best_coupon = Coupon.objects.filter(is_active=True).order_by('-discount_percentage').first()
    discount = min(max((best_coupon.discount_percentage if best_coupon else 0), 0), 90) / 100
    return full_price * (1 - discount)


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
            return [IsOwnerOrStaff()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        # Always allow detail actions (update_status, destroy, retrieve, toggle_favorite) to find PENDING properties
        if self.action in ['update_status', 'destroy', 'retrieve', 'update', 'partial_update', 'toggle_favorite']:
            return Property.objects.all().order_by('-created_at')

        is_admin_view = self.request.query_params.get('admin') == 'true'
        if is_admin_view and is_staff_user(self.request.user):
            return Property.objects.all().order_by('-created_at')

        return Property.objects.filter(status='APPROVED').order_by('-created_at')

    def retrieve(self, request, *args, **kwargs):
        # Non-approved listings are only visible to their owner and staff
        instance = self.get_object()
        if instance.status != 'APPROVED' and not is_staff_user(request.user) and instance.owner_id != getattr(request.user, 'id', None):
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(instance).data)

    def perform_create(self, serializer):
        # 1. Save main property data with status='PENDING'
        property_instance = serializer.save(owner=self.request.user, status='PENDING')

        # 2. Upload images to Cloudinary (with fallback to default storage)
        images = self.request.FILES.getlist('uploaded_images')
        for image in images:
            full_image_url = None
            try:
                if getattr(settings, 'CLOUDINARY_CLOUD_NAME', None) and getattr(settings, 'CLOUDINARY_API_KEY', None):
                    upload_res = cloudinary.uploader.upload(
                        image,
                        folder="setmystay/property_images",
                        resource_type="auto"
                    )
                    full_image_url = upload_res.get('secure_url') or upload_res.get('url')
            except Exception as ce:
                print("Cloudinary image upload note, falling back:", ce)

            if not full_image_url:
                try:
                    file_path = default_storage.save(f'property_images/{image.name}', ContentFile(image.read()))
                    full_image_url = default_storage.url(file_path)
                except Exception as fe:
                    print("Default storage image fallback note:", fe)

            if full_image_url:
                ListingImage.objects.create(property=property_instance, image_url=full_image_url, is_video=False)

        if not property_instance.images.exists():
            ListingImage.objects.create(
                property=property_instance,
                image_url='https://placehold.co/600x400?text=Property+Image',
                is_video=False
            )

        # 3. Upload video to Cloudinary if provided
        video_file = self.request.FILES.get('uploaded_video')
        if video_file:
            full_video_url = None
            try:
                if getattr(settings, 'CLOUDINARY_CLOUD_NAME', None) and getattr(settings, 'CLOUDINARY_API_KEY', None):
                    upload_res = cloudinary.uploader.upload_large(
                        video_file,
                        folder="setmystay/property_videos",
                        resource_type="video"
                    )
                    full_video_url = upload_res.get('secure_url') or upload_res.get('url')
            except Exception as ve:
                print("Cloudinary video upload note, falling back:", ve)

            if not full_video_url:
                try:
                    video_path = default_storage.save(f'property_videos/{video_file.name}', ContentFile(video_file.read()))
                    full_video_url = default_storage.url(video_path)
                except Exception as fe:
                    print("Default storage video fallback note:", fe)

            if full_video_url:
                ListingImage.objects.create(property=property_instance, image_url=full_video_url, is_video=True)

        # 4. Upload verification documents (Aadhaar, Electricity Bill, NOC) to Cloudinary
        for doc_field in ['document_aadhaar', 'document_electricity', 'document_noc']:
            doc_file = self.request.FILES.get(doc_field)
            if doc_file and getattr(settings, 'CLOUDINARY_CLOUD_NAME', None) and getattr(settings, 'CLOUDINARY_API_KEY', None):
                try:
                    upload_res = cloudinary.uploader.upload(
                        doc_file,
                        folder="setmystay/verification_docs",
                        resource_type="auto"
                    )
                    doc_url = upload_res.get('secure_url') or upload_res.get('url')
                    if doc_url:
                        setattr(property_instance, doc_field, doc_url)
                        property_instance.save(update_fields=[doc_field])
                except Exception as doc_err:
                    print(f"Cloudinary {doc_field} upload note:", doc_err)

        # 5. Save Amenities
        try:
            amenities_str = self.request.data.get('amenities_list', '')
            if amenities_str:
                if isinstance(amenities_str, list):
                    amenities_str = ','.join(amenities_str)
                amenity_names = [
                    a.replace('[', '').replace(']', '').replace('"', '').strip()
                    for a in str(amenities_str).split(',')
                    if a.strip()
                ]
                for name in amenity_names:
                    if name:
                        amenity_obj, _ = Amenity.objects.get_or_create(name=name)
                        property_instance.amenities.add(amenity_obj)
        except Exception as e:
            print("Amenity save note:", e)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def toggle_favorite(self, request, pk=None):
        """Send {"liked": true/false} to set the exact state (safe to repeat); without it, flips the state."""
        property_instance = self.get_object()
        user = request.user
        wanted = request.data.get('liked', None)
        if wanted is None:
            liked = not property_instance.favorited_by.filter(pk=user.pk).exists()
        else:
            liked = str(wanted).lower() in ('true', '1', 'yes')
        if liked:
            property_instance.favorited_by.add(user)
        else:
            property_instance.favorited_by.remove(user)
        return Response({'status': 'added' if liked else 'removed', 'liked': liked})

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
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

    def get_permissions(self):
        if self.action in ['destroy', 'update', 'partial_update']:
            return [IsOwnerOrStaff()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['location_preference', 'is_smoker', 'has_pets']

    def get_queryset(self):
        if self.action in ['update_status', 'destroy', 'retrieve', 'update', 'partial_update']:
            return RoommateProfile.objects.all().order_by('-id')
        is_admin_view = self.request.query_params.get('admin') == 'true'
        if is_admin_view and is_staff_user(self.request.user):
            return RoommateProfile.objects.all().order_by('-id')
        return RoommateProfile.objects.filter(status='APPROVED').order_by('-id')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status='PENDING')

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
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
    permission_classes = [ReadOnlyOrStaff]


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
    permission_classes = [ReadOnlyOrSuperAdmin]


class AdvertisementViewSet(viewsets.ModelViewSet):
    queryset = Advertisement.objects.all().order_by('-created_at')
    serializer_class = AdvertisementSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    permission_classes = [ReadOnlyOrSuperAdmin]

    def perform_create(self, serializer):
        image_file = self.request.FILES.get('image')
        cloudinary_url = None
        if image_file and getattr(settings, 'CLOUDINARY_CLOUD_NAME', None) and getattr(settings, 'CLOUDINARY_API_KEY', None):
            try:
                upload_res = cloudinary.uploader.upload(
                    image_file,
                    folder="setmystay/advertisements",
                    resource_type="auto"
                )
                cloudinary_url = upload_res.get('secure_url') or upload_res.get('url')
            except Exception as ce:
                print("Cloudinary ad upload note, falling back:", ce)
        
        instance = serializer.save()
        if cloudinary_url:
            instance.image = cloudinary_url
            instance.save(update_fields=['image'])

    def perform_update(self, serializer):
        image_file = self.request.FILES.get('image')
        cloudinary_url = None
        if image_file and getattr(settings, 'CLOUDINARY_CLOUD_NAME', None) and getattr(settings, 'CLOUDINARY_API_KEY', None):
            try:
                upload_res = cloudinary.uploader.upload(
                    image_file,
                    folder="setmystay/advertisements",
                    resource_type="auto"
                )
                cloudinary_url = upload_res.get('secure_url') or upload_res.get('url')
            except Exception as ce:
                print("Cloudinary ad update note, falling back:", ce)
        
        instance = serializer.save()
        if cloudinary_url:
            instance.image = cloudinary_url
            instance.save(update_fields=['image'])


class StaffViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_staff=True, is_superuser=False).order_by('-date_joined')
    serializer_class = StaffSerializer
    permission_classes = [IsSuperAdmin]

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
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        amount = request.data.get("amount")
        property_id = request.data.get("property_id")
        plan_name = request.data.get("plan_name", "Listing Fee")

        if not amount:
            return Response({"error": "Amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parsed_amount = float(amount)
            if parsed_amount <= 0:
                return Response({"error": "Amount must be greater than zero"}, status=status.HTTP_400_BAD_REQUEST)

            # Unlock plans: the price must match the admin's pricing (minus at most the best active coupon)
            if pricing_key_for_plan(plan_name) and parsed_amount + 1 < minimum_plan_price(plan_name):
                return Response({"error": "Amount does not match the plan price"}, status=status.HTTP_400_BAD_REQUEST)

            client = get_razorpay_client()
            user_id_str = str(request.user.id) if (request.user and request.user.is_authenticated) else ""
            order_data = {
                "amount": int(parsed_amount * 100),
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
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "key": settings.RAZORPAY_KEY_ID,
                "key_id": settings.RAZORPAY_KEY_ID
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
    Called right after the Razorpay popup succeeds.
    - Checks the Razorpay signature (so nobody can fake a payment).
    - Uses the amount Razorpay actually charged, not what the browser says.
    - Saves the Purchase against the logged-in user. Unlock credits / Ultimate
      are then calculated from these Purchase rows (see entitlements.py).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        property_id = request.data.get('property_id')
        payment_id = (request.data.get('razorpay_payment_id') or '').strip()
        order_id = (request.data.get('razorpay_order_id') or '').strip()
        signature = (request.data.get('razorpay_signature') or '').strip()
        plan_name = request.data.get('plan_name') or ('Property Listing Fee' if property_id else 'Subscription Plan')

        if not (payment_id and order_id and signature):
            return Response({'error': 'Missing Razorpay payment details'}, status=status.HTTP_400_BAD_REQUEST)

        client = get_razorpay_client()
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature,
            })
        except Exception:
            return Response({'error': 'Payment signature is invalid'}, status=status.HTTP_400_BAD_REQUEST)

        # Amount actually paid, from Razorpay (paise -> rupees)
        try:
            order = client.order.fetch(order_id)
            paid_amount = (order.get('amount_paid') or order.get('amount') or 0) / 100
        except Exception:
            paid_amount = float(request.data.get('amount') or 0)

        # Unlock plans: make sure the price paid matches the plan (allowing the best active coupon)
        if pricing_key_for_plan(plan_name) and paid_amount + 1 < minimum_plan_price(plan_name):
            return Response({'error': 'Amount paid does not match the plan price'}, status=status.HTTP_400_BAD_REQUEST)

        # Property listing fee: send the property for admin approval
        if property_id:
            prop = Property.objects.filter(id=property_id, owner=user).first()
            if prop and prop.status not in ['APPROVED', 'REJECTED']:
                prop.status = 'PENDING'
                prop.save()
        elif 'listing' in str(plan_name).lower():
            latest_prop = Property.objects.filter(owner=user).order_by('-created_at').first()
            if latest_prop and latest_prop.status not in ['APPROVED', 'REJECTED']:
                latest_prop.status = 'PENDING'
                latest_prop.save()

        Purchase.objects.get_or_create(
            razorpay_payment_id=payment_id,
            defaults={
                'user': user,
                'plan_name': plan_name,
                'amount': paid_amount,
                'status': 'SUCCESS',
            }
        )

        return Response({
            'status': 'success',
            'message': 'Payment verified and recorded successfully',
            'plan': get_entitlement(user),
        }, status=status.HTTP_200_OK)


class MyPurchasesView(generics.ListAPIView):
    """Purchases of the logged-in user only (no more lookup by email)."""
    serializer_class = PurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Purchase.objects.filter(user=self.request.user).order_by('-created_at')


class AllPurchasesAdminView(generics.ListAPIView):
    serializer_class = PurchaseSerializer
    permission_classes = [IsSuperAdmin]
    queryset = Purchase.objects.all().order_by('-created_at')


class MyPlanView(APIView):
    """Everything the site needs after login: credits left, Ultimate status, unlocked listings."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(get_entitlement(request.user), status=status.HTTP_200_OK)


class UserUnlocksView(APIView):
    """Returns the list of listing IDs unlocked by the logged-in user."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ids = list(UserUnlock.objects.filter(user=request.user).values_list('property_id', flat=True))
        return Response({'unlocked_ids': ids}, status=status.HTTP_200_OK)


class UnlockListingView(APIView):
    """Unlocks a listing for the logged-in user, using 1 credit unless Ultimate is active."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        property_id = str(request.data.get('property_id') or '').strip()
        if not property_id:
            return Response({'error': 'property_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        if UserUnlock.objects.filter(user=user, property_id=property_id).exists():
            return Response({'status': 'already_unlocked', 'plan': get_entitlement(user)}, status=status.HTTP_200_OK)

        # Only real, live listings can be unlocked (so a paid credit is never spent on nothing)
        if not property_id.isdigit() or not Property.objects.filter(id=int(property_id), status='APPROVED').exists():
            return Response({'error': 'This listing is not available.'}, status=status.HTTP_404_NOT_FOUND)

        plan = get_entitlement(user)
        if not plan['is_unlimited'] and plan['credits_left'] <= 0:
            return Response({'error': 'No unlock credits left. Please buy a plan.', 'plan': plan},
                            status=status.HTTP_402_PAYMENT_REQUIRED)

        UserUnlock.objects.get_or_create(user=user, property_id=property_id)
        plan = get_entitlement(user)
        return Response({'status': 'success', 'unlocked_ids': plan['unlocked_ids'], 'plan': plan},
                        status=status.HTTP_200_OK)


DEFAULT_PRICING = {
    "unlocks": {"1": 49, "5": 199, "10": 399, "unlimited": 999},
    "listings": {"roommate": 149, "pg": 349, "rental": 999}
}

DEFAULT_APP_SETTINGS = {'swipe_limit': 25, 'swipe_reset_hours': 24, 'slot_cooldown_hours': 24}


def get_app_settings():
    cfg = PricingConfig.objects.filter(key='global_pricing').first()
    stored = ((cfg.pricing_data or {}).get('settings') if cfg else None) or {}
    return {**DEFAULT_APP_SETTINGS, **stored}


IST = ZoneInfo('Asia/Kolkata')


def next_ist_midnight(now=None):
    now_ist = (now or timezone.now()).astimezone(IST)
    tomorrow = (now_ist + timedelta(days=1)).date()
    return datetime.combine(tomorrow, dt_time.min, tzinfo=IST)


class SwipesView(APIView):
    """Roommate swipes per account, stored on the server. Every day at 12:00 AM IST the
    count goes back to 0, so the user gets the admin's 'swipes per account' again."""
    permission_classes = [permissions.IsAuthenticated]

    def _state(self, usage, cfg):
        return {
            'limit': cfg['swipe_limit'],
            'used': usage.count,
            'left': max(0, cfg['swipe_limit'] - usage.count),
            'resets_at': next_ist_midnight().isoformat(),
        }

    def _usage(self, user, lock=False):
        qs = SwipeUsage.objects.select_for_update() if lock else SwipeUsage.objects
        usage, _ = qs.get_or_create(user=user)
        today_ist = timezone.now().astimezone(IST).date()
        if usage.window_start.astimezone(IST).date() != today_ist:
            usage.count = 0
            usage.window_start = timezone.now()
            usage.save(update_fields=['count', 'window_start'])
        return usage

    def get(self, request):
        cfg = get_app_settings()
        return Response(self._state(self._usage(request.user), cfg))

    def post(self, request):
        cfg = get_app_settings()
        with transaction.atomic():
            usage = self._usage(request.user, lock=True)
            if usage.count >= cfg['swipe_limit']:
                return Response({**self._state(usage, cfg), 'error': 'No swipes left'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            usage.count += 1
            usage.save(update_fields=['count'])
        return Response(self._state(usage, cfg))


class SwipeUndoView(APIView):
    """Undo on the swipe deck gives the last swipe back (never below 0, today's count only)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cfg = get_app_settings()
        view = SwipesView()
        with transaction.atomic():
            usage = view._usage(request.user, lock=True)
            if usage.count > 0:
                usage.count -= 1
                usage.save(update_fields=['count'])
        return Response(view._state(usage, cfg))


class PricingConfigView(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsSuperAdmin()]
        return [permissions.AllowAny()]

    def get(self, request):
        cfg = PricingConfig.objects.filter(key='global_pricing').first()
        data = dict(cfg.pricing_data) if cfg and cfg.pricing_data else dict(DEFAULT_PRICING)
        data['settings'] = get_app_settings()
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data
        if not isinstance(data, dict):
            return Response({"error": "Invalid pricing payload"}, status=status.HTTP_400_BAD_REQUEST)
        data = dict(data)
        # Swipe / slot-machine settings set by the admin are stored with the pricing
        cfg_old = PricingConfig.objects.filter(key='global_pricing').first()
        old_settings = ((cfg_old.pricing_data or {}).get('settings') if cfg_old else None) or {}
        incoming = data.get('settings') or {}
        merged = {**DEFAULT_APP_SETTINGS, **old_settings}
        for k in DEFAULT_APP_SETTINGS:
            if k in incoming:
                try:
                    v = int(incoming[k])
                except (TypeError, ValueError):
                    return Response({"error": f"Invalid value for {k}"}, status=status.HTTP_400_BAD_REQUEST)
                if v < 1 or v > 10000:
                    return Response({"error": f"{k} must be between 1 and 10000"}, status=status.HTTP_400_BAD_REQUEST)
                merged[k] = v
        data['settings'] = merged
        for section in ('unlocks', 'listings'):
            prices = data.get(section)
            if not isinstance(prices, dict) or not prices:
                return Response({"error": f"Missing {section} prices"}, status=status.HTTP_400_BAD_REQUEST)
            for plan, price in prices.items():
                try:
                    ok = float(price) > 0
                except (TypeError, ValueError):
                    ok = False
                if not ok:
                    return Response({"error": f"Price for {section} '{plan}' must be a number above 0"}, status=status.HTTP_400_BAD_REQUEST)
        cfg, _ = PricingConfig.objects.update_or_create(
            key='global_pricing',
            defaults={'pricing_data': data}
        )
        return Response(cfg.pricing_data, status=status.HTTP_200_OK)


class VerifyAdminView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (user.is_staff or user.is_superuser):
            return Response(
                {"error": "Forbidden. Staff or superuser access required."},
                status=status.HTTP_403_FORBIDDEN
            )
        return Response({
            "status": "ok",
            "username": user.username,
            "email": user.email,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        }, status=status.HTTP_200_OK)


class VerifyStaffView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (user.is_staff or user.is_superuser):
            return Response(
                {"error": "Forbidden. Staff or superuser access required."},
                status=status.HTTP_403_FORBIDDEN
            )
        return Response({
            "status": "ok",
            "username": user.username,
            "email": user.email,
            "is_staff": user.is_staff,
        }, status=status.HTTP_200_OK)

class ChangePasswordView(APIView):
    """Lets a logged-in admin/staff change their own password (used by Admin > Security Settings)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password') or ''
        new_password = request.data.get('new_password') or ''
        user = request.user
        if not user.check_password(old_password):
            return Response({'error': 'Current password is not correct.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_password) < 8:
            return Response({'error': 'New password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        if new_password == old_password:
            return Response({'error': 'New password must be different.'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save(update_fields=['password'])
        # A new password signs out every remembered admin device (they need the email code again)
        from .models import TrustedAdminDevice
        TrustedAdminDevice.objects.filter(user=user).delete()
        return Response({'status': 'success'}, status=status.HTTP_200_OK)


DEFAULT_SITE_CONTACT = {
    'email': 'setmystay02@gmail.com',
    'phone': '+91 79771 69550',
    'address': 'Office no. 01, Neelsidhi Splendour, Sector 15, CBD Belapur, Navi Mumbai, Maharashtra 400614',
}


class SiteContactView(APIView):
    """Footer contact details. Everyone can read; only the main admin can change them."""

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsSuperAdmin()]
        return [permissions.AllowAny()]

    def get(self, request):
        cfg = PricingConfig.objects.filter(key='site_contact').first()
        data = {**DEFAULT_SITE_CONTACT, **((cfg.pricing_data if cfg else None) or {})}
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        email = str(request.data.get('email') or '').strip()
        phone = str(request.data.get('phone') or '').strip()
        address = str(request.data.get('address') or '').strip()
        if '@' not in email or len(email) > 200:
            return Response({'error': 'Please enter a valid email.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(''.join(c for c in phone if c.isdigit())) < 10 or len(phone) > 30:
            return Response({'error': 'Please enter a valid phone number.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(address) < 5 or len(address) > 500:
            return Response({'error': 'Please enter the address.'}, status=status.HTTP_400_BAD_REQUEST)
        data = {'email': email, 'phone': phone, 'address': address}
        PricingConfig.objects.update_or_create(key='site_contact', defaults={'pricing_data': data})
        return Response(data, status=status.HTTP_200_OK)


class MyFavoritesView(APIView):
    """IDs of the listings the logged-in user has liked (so likes survive logout / clearing cookies)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ids = [str(i) for i in request.user.favorite_properties.values_list('id', flat=True)]
        return Response({'ids': ids}, status=status.HTTP_200_OK)
