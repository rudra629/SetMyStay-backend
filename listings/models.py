from django.db import models
from django.conf import settings # To link to our custom User model

# 1. Amenities (WiFi, AC, Gym) - Stored separately so we can filter by them
class Amenity(models.Model):
    name = models.CharField(max_length=50)
    icon_code = models.CharField(max_length=50, blank=True, help_text="Lucide React icon name")

    def __str__(self):
        return self.name

# 2. The Main Property Listing (Rentals & PGs)
class Property(models.Model):
    # Choices
    class Types(models.TextChoices):
        RENTAL = 'RENTAL', 'Rental (Full House)'
        PG = 'PG', 'PG / Co-living'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'   # 🟡 Default
        APPROVED = 'APPROVED', 'Approved'       # 🟢 Live on Site
        REJECTED = 'REJECTED', 'Rejected'       # 🔴 Hidden
        RENTED = 'RENTED', 'Rented Out'         # ⚪ Archived

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='properties')
    
    # Basic Info
    title = models.CharField(max_length=200)
    description = models.TextField()
    property_type = models.CharField(max_length=10, choices=Types.choices)
    
    # Money Matters
    rent = models.IntegerField()
    deposit = models.IntegerField()
    is_negotiable = models.BooleanField(default=False)

    # Location
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=100) # e.g., "Nerul", "Vashi"
    address = models.TextField()

    # Property Specs
    bhk = models.CharField(max_length=20, blank=True) # "2BHK", "3BHK"
    furnishing = models.CharField(max_length=20, blank=True) # "Full", "Semi", "None"
    sq_ft = models.IntegerField(null=True, blank=True)
    
    # PG Specifics (Only used if type is PG)
    occupancy_type = models.CharField(max_length=50, blank=True) # "Single", "Double Sharing"
    gender_preference = models.CharField(max_length=20, blank=True) # "Male", "Female", "Any"

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
    image_url = models.URLField() # We will store the Firebase URL here
    is_video = models.BooleanField(default=False)

# 4. Roommate Finder Profiles
class RoommateProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Preferences
    budget = models.IntegerField()
    location_preference = models.CharField(max_length=100)
    move_in_date = models.DateField(null=True, blank=True)
    
    # Lifestyle (Crucial for filtering)
    is_smoker = models.BooleanField(default=False)
    is_drinker = models.BooleanField(default=False)
    has_pets = models.BooleanField(default=False)
    occupation = models.CharField(max_length=100, blank=True)
    
    # 🛡️ STAFF CONTROL
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    
    def __str__(self):
        return f"Roommate: {self.user.username}"