from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # User Roles
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        STAFF = 'STAFF', 'Staff'
        OWNER = 'OWNER', 'Property Owner'
        SEEKER = 'SEEKER', 'Seeker/Tenant'

    role = models.CharField(max_length=10, choices=Roles.choices, default=Roles.SEEKER)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.URLField(blank=True, null=True)
    
    # For Staff Performance Tracking
    approved_count = models.IntegerField(default=0)
    rejected_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.username} ({self.role})"