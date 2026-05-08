from rest_framework import serializers
from .models import Property, Amenity, ListingImage, RoommateProfile, Coupon, Advertisement # Make sure to import them!
from django.contrib.auth.models import User
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
        queryset=Amenity.objects.all(), many=True, write_only=True, source='amenities'
    )
    
    # ❌ (I completely removed the line that was hijacking your username!)

    class Meta:
        model = Property
        fields = [
            'id', 'title', 'description', 'property_type', 'status',
            'rent', 'deposit', 'is_negotiable',
            'city', 'area', 'address',
            'bhk', 'furnishing', 'sq_ft',
            'occupancy_type', 'gender_preference',
            'sharing_status', 'is_broker', 
            
            # 👇 ADDED: The new contact fields from your model
            'owner_name', 'phone_primary', 'phone_secondary',
            'document_aadhaar', 'document_electricity', 'document_noc',
            'images', 'amenities', 'amenity_ids', 'created_at'
        ]

# 4. Roommate Profile Serializer
class RoommateProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = RoommateProfile
        fields = '__all__'

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'discount_percentage', 'is_active', 'created_at']

class AdvertisementSerializer(serializers.ModelSerializer):
    # Sends the URL to Next.js (Read Only)
    imageUrl = serializers.ImageField(source='image', read_only=True)
    
    # Catches the File from Next.js (Write Only)
    image = serializers.ImageField(write_only=True, required=False)
    
    class Meta:
        model = Advertisement
        # Make sure 'image' is added to this list!
        fields = ['id', 'title', 'description', 'imageUrl', 'image', 'is_active', 'created_at']

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