from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile

class UserProfileSerializer(serializers.ModelSerializer):
    gender = serializers.CharField(source='profile.gender', required=False)
    age = serializers.IntegerField(source='profile.age', required=False)
    
    # Make phone_number and role REQUIRED for the profile completion step
    phone_number = serializers.CharField(source='profile.phone_number', required=True)
    role = serializers.ChoiceField(choices=Profile.Roles.choices, source='profile.role', required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'gender', 'age', 'phone_number', 'role']
        read_only_fields = ['email'] # They can't change their Google email

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        
        # Update User model fields
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.save()

        # Update Profile model fields
        profile = instance.profile
        profile.gender = profile_data.get('gender', profile.gender)
        profile.age = profile_data.get('age', profile.age)
        profile.phone_number = profile_data.get('phone_number', profile.phone_number)
        profile.role = profile_data.get('role', profile.role)
        
        # If they successfully submitted the required fields, mark as complete!
        if profile.phone_number and profile.role:
            profile.is_profile_complete = True
            
        profile.save()
        return instance