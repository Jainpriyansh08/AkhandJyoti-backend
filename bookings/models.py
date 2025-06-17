import uuid
from django.db import models
from django.conf import settings
from users.models import Patient, StaffMember
from django.utils import timezone
from django.core.validators import MinValueValidator
from users.models import User
from packages.models import Package, Coupon
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
    account = models.ForeignKey(User, on_delete=models.PROTECT)
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
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
        return f"Booking #{self.id} - {self.account.mobile_number}"

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
            
        super().save(*args, **kwargs)

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
