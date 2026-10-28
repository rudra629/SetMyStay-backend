from django.contrib import admin
from .models import Property, Amenity, ListingImage, RoommateProfile

# This allows you to upload images directly on the Property creation page!
class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'property_type', 'rent', 'city', 'status')
    list_filter = ('status', 'property_type', 'city', 'is_broker')
    search_fields = ('title', 'area', 'city', 'owner_name')
    list_editable = ('status',) # Lets you approve/reject directly from the list view
    inlines = [ListingImageInline]

@admin.register(RoommateProfile)
class RoommateProfileAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'location_preference', 'budget', 'status')
    list_filter = ('status',)
    search_fields = ('user_name', 'location_preference')
    list_editable = ('status',)

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)