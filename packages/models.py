from django.db import models

# Create your models here.

class Package(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    base_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

class Coupon(models.Model):
    COUPON_TYPES = (
        ('ONLINE_DEFAULT', 'Online Default'),
        ('BULK_BOOKING', 'Bulk Booking'),
        ('PROMOTIONAL', 'Promotional'),
    )
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPES)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    max_uses = models.IntegerField(null=True, blank=True)
    uses_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
