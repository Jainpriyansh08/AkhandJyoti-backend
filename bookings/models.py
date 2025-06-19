import uuid
from django.db import models
from django.conf import settings
from users.models import Patient, StaffMember
from django.utils import timezone
from django.core.validators import MinValueValidator
from users.models import User
from packages.models import Package
from coupons.models import Coupon
from django.db.models import Q

# Create your models here.

class BookingSlot(models.Model):
    id = models.AutoField(primary_key=True)
    date = models.DateField()
    time = models.TimeField()
    total_slots = models.IntegerField(default=20)
    available_slots = models.IntegerField()
    is_holiday = models.BooleanField(default=False)
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('date', 'time', 'package')

    def __str__(self):
        return f"{self.date} {self.time} - {self.package.name}"

    def save(self, *args, **kwargs):
        if not self.id:  # Only set available_slots when creating
            self.available_slots = self.total_slots
        super().save(*args, **kwargs)

class BookingOrder(models.Model):
    STATUS_CHOICES = (
        ('IN_PROGRESS', 'In Progress'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )

    id = models.AutoField(primary_key=True)
    booking_slot = models.ForeignKey(BookingSlot, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    online_coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='online_bookings')
    promotional_coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='promotional_bookings')
    online_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    promotional_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_assisted_booking = models.BooleanField(default=False)
    assisted_by = models.ManyToManyField(StaffMember, blank=True)
    number_of_members = models.IntegerField(default=1)
    resource_hold_time = models.DateTimeField(null=True, blank=True, help_text="Timestamp for when slots were held")
    his_invoice_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
    his_invoice_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking #{self.id} - {self.user.mobile_number}"

    def save(self, *args, **kwargs):
        if not self.id and self.status == 'IN_PROGRESS':
            # Check if there's enough capacity
            if self.booking_slot.available_slots >= self.number_of_members:
                self.booking_slot.available_slots -= self.number_of_members
                self.booking_slot.save()
            else:
                raise ValueError("Not enough slots available")
            
            # Set resource hold time
            self.resource_hold_time = timezone.now()
            
            # Set amounts
            self.total_amount = self.package.base_amount * self.number_of_members
            self.final_amount = self.total_amount
            
            # If coupons are provided during creation, apply them
            if hasattr(self, '_online_coupon_code'):
                self.apply_coupon(self._online_coupon_code)
            if hasattr(self, '_promotional_coupon_code'):
                self.apply_coupon(self._promotional_coupon_code)
            
        super().save(*args, **kwargs)

    def apply_coupon(self, coupon_code):
        """Apply a pre-validated coupon to the booking"""
        from django.core.exceptions import ValidationError
        from django.db import transaction

        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
        except Coupon.DoesNotExist:
            raise ValidationError("Invalid coupon code")

        # For promotional coupons, check if one is already applied
        if coupon.coupon_type in ['PROMOTIONAL', 'BULK_BOOKING'] and self.promotional_coupon:
            raise ValidationError("A promotional coupon has already been applied")

        with transaction.atomic():
            # Calculate discount
            discount = coupon.calculate_discount(self.final_amount)
            
            # Apply coupon
            if coupon.coupon_type == 'ONLINE_DEFAULT':
                self.online_coupon = coupon
                self.online_discount = discount
            else:
                # Update usage count for non-default coupons
                coupon.current_uses += 1
                coupon.save()
                self.promotional_coupon = coupon
                self.promotional_discount = discount

            # Update final amount
            self.final_amount -= discount
            self.save()

        return discount

    def remove_coupon(self, coupon_code):
        from django.core.exceptions import ValidationError
        from django.db import transaction

        try:
            coupon = Coupon.objects.get(code=coupon_code)
        except Coupon.DoesNotExist:
            raise ValidationError("Invalid coupon code")

        # Don't allow removing ONLINE_DEFAULT coupons
        if coupon.coupon_type == 'ONLINE_DEFAULT':
            raise ValidationError("Cannot remove default online coupon")

        with transaction.atomic():
            if self.promotional_coupon and self.promotional_coupon.code == coupon_code:
                discount = self.promotional_discount
                self.promotional_coupon = None
                self.promotional_discount = 0
                
                # Restore the discount amount to final_amount
                self.final_amount += discount
                self.save()

                # Decrease coupon usage count
                coupon.current_uses -= 1
                coupon.save()
            else:
                raise ValidationError("Coupon not found on this order")

        return discount

class BookingMember(models.Model):
    id = models.AutoField(primary_key=True)
    booking = models.ForeignKey(BookingOrder, on_delete=models.CASCADE, related_name='members')
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    is_primary_contact = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('booking', 'patient')

    def __str__(self):
        return f"{self.patient.first_name} {self.patient.last_name} - Booking #{self.booking.id}"
