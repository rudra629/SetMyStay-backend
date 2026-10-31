from rest_framework import serializers
from .models import Coupon, Advertisement

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'