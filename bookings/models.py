import uuid
from django.db import models
from django.conf import settings

# Create your models here.

class BookingSlot(models.Model):
    id = models.AutoField(primary_key=True)
    date = models.DateField()
    time = models.TimeField()
    total_slots = models.IntegerField(default=20)
    available_slots = models.IntegerField()
    is_holiday = models.BooleanField(default=False)
    package = models.ForeignKey('packages.Package', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('date', 'time', 'package')

class BookingOrder(models.Model):
    STATUS_CHOICES = (
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('FAILED', 'Failed'),
        ('PAYMENT_ABANDONED', 'Payment Abandoned'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    booking_slot = models.ForeignKey(BookingSlot, on_delete=models.PROTECT)
    package = models.ForeignKey('packages.Package', on_delete=models.PROTECT)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    coupon_applied = models.ForeignKey('packages.Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    is_assisted_booking = models.BooleanField(default=False)
    assisted_by = models.ManyToManyField('users.StaffMember', blank=True)
    number_of_members = models.IntegerField(default=1)
    resource_hold_time = models.DateTimeField(null=True, blank=True, help_text="Timestamp for when slots/coupons were held for cleanup.")
    his_invoice_generated = models.BooleanField(default=False)
    his_invoice_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

class BookingMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_order = models.ForeignKey(BookingOrder, on_delete=models.CASCADE, related_name='members')
    patient = models.ForeignKey('users.Patient', on_delete=models.PROTECT)
    individual_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_primary_contact = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
