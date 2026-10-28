from django.contrib import admin
from .models import Coupon, Advertisement 

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('code',)
    list_editable = ('is_active',) # Quickly toggle coupons on/off for the slot machine

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active',)
    list_editable = ('is_active',)