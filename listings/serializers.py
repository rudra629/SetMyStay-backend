from rest_framework import serializers
from .models import Property, Amenity, ListingImage, RoommateProfile, Coupon, Advertisement # Make sure to import them!
from django.contrib.auth.models import User
from .models import Purchase, HeroBannerAd
from .roommate_form import clean_roommate_details, public_roommate_details
# 1. Image Serializer
class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ['id', 'image_url', 'is_video']

# 2. Amenity Serializer
class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'icon_code']

# 3. Main Property Serializer
class PropertySerializer(serializers.ModelSerializer):
    images = ListingImageSerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    
    # We also allow sending amenity IDs when creating a listing
    amenity_ids = serializers.PrimaryKeyRelatedField(
        queryset=Amenity.objects.all(), many=True, write_only=True, source='amenities', required=False
    )
    
    # ❌ (I completely removed the line that was hijacking your username!)

    class Meta:
        model = Property
        fields = [
            'id', 'title', 'description', 'property_type', 'status',
            'rent', 'deposit', 'is_negotiable',
            'city', 'area', 'address', 'state', 'vendor_number',
            'bhk', 'furnishing', 'sq_ft',
            'occupancy_type', 'gender_preference',
            'sharing_status', 'is_broker', 'age', 
            
            # 👇 ADDED: The new contact fields from your model
            'owner_name', 'phone_primary', 'phone_secondary',
            'document_aadhaar', 'document_electricity', 'document_noc',
            'images', 'amenities', 'amenity_ids', 'created_at',
            'roommate_details', 'edited_at',
        ]
        read_only_fields = ['edited_at']

    # Contact details are only sent to: the owner, staff/admin, or a user who unlocked it.
    # Verification documents are only sent to the owner and staff/admin.
    CONTACT_FIELDS = ('phone_primary', 'phone_secondary', 'address', 'vendor_number')
    DOCUMENT_FIELDS = ('document_aadhaar', 'document_electricity', 'document_noc')

    def _unlocked_ids(self, request):
        cached = getattr(request, '_setmystay_unlocked_ids', None)
        if cached is None:
            from .models import UserUnlock
            user = getattr(request, 'user', None)
            if user and user.is_authenticated:
                cached = set(UserUnlock.objects.filter(user=user).values_list('property_id', flat=True))
            else:
                cached = set()
            request._setmystay_unlocked_ids = cached
        return cached

    def validate_roommate_details(self, value):
        if value in (None, ''):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('Invalid roommate details.')
        import json
        if len(json.dumps(value)) > 20000:
            raise serializers.ValidationError('Roommate details are too long.')
        cleaned, missing = clean_roommate_details(value)
        self._roommate_missing = missing
        return cleaned

    def validate(self, attrs):
        attrs = super().validate(attrs)
        ptype = attrs.get('property_type') or (self.instance.property_type if self.instance else '')
        if self.instance is not None and 'property_type' in attrs and attrs['property_type'] != self.instance.property_type:
            request = self.context.get('request')
            user = getattr(request, 'user', None)
            if not (user and (user.is_staff or user.is_superuser)):
                raise serializers.ValidationError({'property_type': 'The listing type cannot be changed.'})
        if str(ptype).upper() == 'ROOMMATE':
            details = attrs.get('roommate_details')
            if self.instance is None and not details:
                raise serializers.ValidationError({'roommate_details': 'Please fill in the roommate questions.'})
            if details:
                missing = getattr(self, '_roommate_missing', [])
                if missing:
                    raise serializers.ValidationError({'roommate_details': 'Please answer: ' + ', '.join(missing[:4]) + ('…' if len(missing) > 4 else '')})
                # Keep the card / filter fields in step with the answers
                attrs['owner_name'] = details.get('first_name') or attrs.get('owner_name')
                attrs['age'] = details.get('age') or attrs.get('age')
                attrs['gender_preference'] = {'male': 'Male', 'female': 'Female', 'nonbinary': 'Other'}.get(details.get('gender'), 'Any')
                attrs['sharing_status'] = 'Living in' if details.get('has_place') == 'has_place' else 'Moving soon'
        elif attrs.get('roommate_details'):
            attrs['roommate_details'] = {}
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        logged_in = bool(user and user.is_authenticated)
        is_staff = logged_in and (user.is_staff or user.is_superuser)
        is_owner = logged_in and instance.owner_id == user.id
        if is_staff:
            # Admin / staff only: edit tracking (normal users never see whether a listing was edited)
            data['pending_edits'] = self._pending_edits(instance)
            return data
        data.pop('edited_at', None)
        if is_owner:
            return data
        unlocked = bool(request and str(instance.id) in self._unlocked_ids(request))
        data['roommate_details'] = public_roommate_details(instance.roommate_details or {}, can_see_private=unlocked)
        for f in self.DOCUMENT_FIELDS:
            data[f] = None
        if not unlocked:
            for f in self.CONTACT_FIELDS:
                data[f] = None
        return data

    @staticmethod
    def _pending_edits(instance):
        """Changes from the not-yet-cleared edit notifications, merged per field (first old -> latest new)."""
        merged = {}
        edits = getattr(instance, '_prefetched_edits', None)
        if edits is None:
            edits = list(instance.edits.filter(cleared=False).order_by('created_at'))
        for e in edits:
            for c in (e.changes or []):
                f = c.get('field')
                if not f:
                    continue
                if f in merged:
                    merged[f]['new'] = c.get('new')
                else:
                    merged[f] = {'field': f, 'old': c.get('old'), 'new': c.get('new')}
        return [m for m in merged.values() if m['old'] != m['new']]

# 4. Roommate Profile Serializer
class RoommateProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = RoommateProfile
        fields = '__all__'

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'discount_percentage', 'is_active', 'scope', 'created_at']

class AdvertisementSerializer(serializers.ModelSerializer):
    # Sends the URL to Next.js (Read Only)
    imageUrl = serializers.ImageField(source='image', read_only=True)
    
    # Catches the File from Next.js (Write Only)
    image = serializers.ImageField(write_only=True, required=False)
    
    class Meta:
        model = Advertisement
        # Make sure 'image' is added to this list!
        fields = ['id', 'title', 'description', 'imageUrl', 'image', 'is_active', 'coupon_codes', 'created_at']

# 👇 ADD THIS TO THE BOTTOM 👇
class StaffSerializer(serializers.ModelSerializer):
    # Make password write-only so it never gets sent back to the frontend!
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'password', 'is_active']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        user.is_staff = True # Ensure they get staff privileges!
        if password:
            user.set_password(password) # Safely hash the password
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password) # Safely hash new password
        instance.save()
        return instance
class PurchaseSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = ['id', 'user_name', 'user_email', 'plan_name', 'amount', 'razorpay_payment_id', 'status', 'created_at']

    def get_user_name(self, obj):
        if obj.user:
            full = f"{obj.user.first_name} {obj.user.last_name}".strip()
            if full:
                return full
            if obj.user.username:
                return obj.user.username
        return 'Customer'

    def get_user_email(self, obj):
        if obj.user and obj.user.email:
            return obj.user.email
        if obj.user and '@' in obj.user.username:
            return obj.user.username
        return ''


class HeroBannerAdSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroBannerAd
        fields = ['id', 'text', 'link_url', 'image_url', 'is_active', 'sort_order', 'created_at']
        read_only_fields = ['id', 'image_url', 'created_at']
