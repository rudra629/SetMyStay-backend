from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Coupon
from .serializers import CouponSerializer

class CouponViewSet(viewsets.ModelViewSet):
    # Only send coupons that are checked as 'Active' in the admin panel
    queryset = Coupon.objects.filter(is_active=True)
    serializer_class = CouponSerializer
    permission_classes = [AllowAny]  # Allows the slot machine to work even if the user isn't logged in