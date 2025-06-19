import uuid
from django.db import models

# Create your models here.

class PaymentTransaction(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    )
    MODE_CHOICES = (
        ('RAZORPAY', 'Razorpay'),
        ('CASH', 'Cash'),
    )
    payment_id = models.AutoField(primary_key=True)
    booking_order = models.ForeignKey('bookings.BookingOrder', on_delete=models.CASCADE, related_name='transactions')
    mode_of_payment = models.CharField(max_length=50, choices=MODE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    provider_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    provider_payment_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    provider_signature = models.CharField(max_length=255, null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
