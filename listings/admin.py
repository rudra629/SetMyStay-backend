from django.contrib import admin
from .models import Property, Amenity, ListingImage, RoommateProfile, Coupon, Advertisement, Purchase

class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'property_type', 'rent', 'city', 'status')
    list_filter = ('status', 'property_type', 'city', 'is_broker')
    search_fields = ('title', 'area', 'city', 'owner_name')
    list_editable = ('status',)
    inlines = [ListingImageInline]

@admin.register(RoommateProfile)
class RoommateProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'location_preference', 'budget', 'status')
    list_filter = ('status',)
    search_fields = ('location_preference',)
    list_editable = ('status',)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'is_active')
    list_editable = ('is_active',)

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    list_editable = ('is_active',)

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('plan_name', 'amount', 'razorpay_payment_id', 'status', 'created_at')
    list_filter = ('status',)

admin.site.register(Amenity)
admin.site.register(ListingImage)