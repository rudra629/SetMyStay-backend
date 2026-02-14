from rest_framework import serializers
from .models import Property, Amenity, ListingImage, RoommateProfile

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
    
    owner_name = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Property
        fields = [
            'id', 'title', 'description', 'property_type', 'status',
            'rent', 'deposit', 'is_negotiable',
            'city', 'area', 'address',
            'bhk', 'furnishing', 'sq_ft',
            'occupancy_type', 'gender_preference',
            'images', 'amenities', 'amenity_ids', 'owner_name', 'created_at'
        ]

# 4. Roommate Profile Serializer
class RoommateProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = RoommateProfile
        fields = '__all__'