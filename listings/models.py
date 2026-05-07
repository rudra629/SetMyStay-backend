from django.db import models
from django.contrib.auth.models import User # Using the standard User since we removed the custom one
from users.models import Profile # If you need to link to the profile later

# 1. Amenities (WiFi, AC, Gym) - Stored separately so we can filter by them
class Amenity(models.Model):
    name = models.CharField(max_length=50)
    icon_code = models.CharField(max_length=50, blank=True, help_text="Lucide React icon name")

    def __str__(self):
        return self.name

# 2. The Main Property Listing (Rentals, PGs, & Roommates)
class Property(models.Model):
    # Choices
    class Types(models.TextChoices):
        RENTAL = 'RENTAL', 'Rental (Full House)'
        PG = 'PG', 'PG / Co-living'
        ROOMMATE = 'ROOMMATE', 'Looking for Roommate'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'   # 🟡 Default
        APPROVED = 'APPROVED', 'Approved'       # 🟢 Live on Site
        REJECTED = 'REJECTED', 'Rejected'       # 🔴 Hidden
        RENTED = 'RENTED', 'Rented Out / Found' # ⚪ Archived

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    
    # Basic Info
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True) 
    property_type = models.CharField(max_length=20, choices=Types.choices) 
    
    # 👇 ADDED: Contact Information
    owner_name = models.CharField(max_length=100, blank=True, null=True)
    phone_primary = models.CharField(max_length=20, blank=True, null=True)
    phone_secondary = models.CharField(max_length=20, blank=True, null=True)

    # Money Matters
    rent = models.IntegerField()
    deposit = models.IntegerField(blank=True, null=True)
    is_negotiable = models.BooleanField(default=False)

    # Location
    city = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True) 
    address = models.TextField(blank=True, null=True)

    # Property Specs
    bhk = models.CharField(max_length=20, blank=True) 
    furnishing = models.CharField(max_length=20, blank=True) 
    sq_ft = models.IntegerField(null=True, blank=True)
    
    # ----------------------------------------------------
    # TYPE-SPECIFIC FIELDS 
    # ----------------------------------------------------

    # PG Specifics
    occupancy_type = models.CharField(max_length=50, blank=True) 
    
    # PG & Roommate Specifics
    gender_preference = models.CharField(max_length=20, blank=True) 
    
    # Roommate Specifics 
    sharing_status = models.CharField(
        max_length=50, 
        choices=[('Living in', 'Yes, living in property'), ('Moving soon', 'Going within a month')],
        null=True, blank=True
    )

    # Rental Specifics 
    is_broker = models.BooleanField(default=False, null=True, blank=True)

    # ----------------------------------------------------

    # Relationships
    amenities = models.ManyToManyField(Amenity, blank=True)
    
    # 🛡️ STAFF CONTROL
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.status})"

# 3. Images for Properties
class ListingImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image_url = models.URLField() 
    is_video = models.BooleanField(default=False)

# 4. Roommate Finder Profiles
class RoommateProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Preferences
    budget = models.IntegerField()
    location_preference = models.CharField(max_length=100)
    move_in_date = models.DateField(null=True, blank=True)
    
    # Lifestyle 
    is_smoker = models.BooleanField(default=False)
    is_drinker = models.BooleanField(default=False)
    has_pets = models.BooleanField(default=False)
    occupation = models.CharField(max_length=100, blank=True)
    
    # 🛡️ STAFF CONTROL
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    
    def __str__(self):
        return f"Roommate: {self.user.username}"