from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile

class UserProfileSerializer(serializers.ModelSerializer):
    gender = serializers.CharField(source='profile.gender', required=False, allow_blank=True, allow_null=True)
    age = serializers.IntegerField(source='profile.age', required=False, allow_null=True)
    phone_number = serializers.CharField(source='profile.phone_number', required=True)
    address = serializers.CharField(source='profile.address', required=False, allow_blank=True, allow_null=True)
    role = serializers.ChoiceField(choices=Profile.Roles.choices, source='profile.role', required=False, default=Profile.Roles.SEEKER)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'gender', 'age', 'phone_number', 'address', 'role']
        read_only_fields = []

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        
        # Update User model fields
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        if 'email' in validated_data and validated_data['email']:
            instance.email = validated_data['email']
        instance.save()

        # Update Profile model fields
        profile = instance.profile
        profile.gender = profile_data.get('gender', profile.gender)
        profile.age = profile_data.get('age', profile.age)
        profile.phone_number = profile_data.get('phone_number', profile.phone_number)
        profile.address = profile_data.get('address', profile.address)
        profile.role = profile_data.get('role', profile.role or Profile.Roles.SEEKER)
        
        # If they successfully submitted the required phone number, mark as complete!
        if profile.phone_number:
            profile.is_profile_complete = True
            
        profile.save()
        return instance