from django.contrib import admin
from .models import Property, Amenity, ListingImage, RoommateProfile

# Import the models from your management app
from management.models import Coupon, Advertisement

# --- LISTINGS APP MODELS ---

class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'property_type', 'rent', 'city', 'status')
    list_filter = ('status', 'property_type', 'city', 'is_broker')
    search_fields = ('title', 'area', 'city', 'owner_name')
    list_editable = ('status',) 
    inlines = [ListingImageInline]
@admin.register(RoommateProfile)
class RoommateProfileAdmin(admin.ModelAdmin):
    # Removed 'user_name' to prevent the crash. Added 'id' as a safe fallback.
    list_display = ('id', 'location_preference', 'budget', 'status')
    list_filter = ('status',)
    search_fields = ('location_preference',)
    list_editable = ('status',)

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

admin.site.register(ListingImage)


# --- MANAGEMENT APP MODELS ---

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('code',)
    list_editable = ('is_active',)

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active',)
    list_editable = ('is_active',)