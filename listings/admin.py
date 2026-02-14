from django.contrib import admin
from .models import Property, Amenity, ListingImage, RoommateProfile

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'property_type', 'rent', 'city', 'status')
    list_filter = ('status', 'property_type', 'city')
    search_fields = ('title', 'area')

admin.site.register(Amenity)
admin.site.register(ListingImage)
admin.site.register(RoommateProfile)