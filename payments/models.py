import uuid
from django.db import models
from django.utils import timezone

# Create your models here.

class PaymentGateway(models.Model):
    """Model to store different payment gateway configurations"""
    name = models.CharField(max_length=50)  # e.g. 'razorpay', 'stripe'
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict)  # Store gateway-specific configuration
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_gateways'

    def __str__(self):
        return self.name

class PaymentTransaction(models.Model):
    """Model to store payment transactions"""
    class PaymentStatus(models.TextChoices):
        INITIATED = 'initiated', 'Initiated'
        PROCESSING = 'processing', 'Processing'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        IDLE = 'idle', 'Idle'
        REFUNDED = 'refunded', 'Refunded'

    order_id = models.CharField(max_length=100, unique=True)
    payment_gateway = models.ForeignKey(PaymentGateway, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.INITIATED
    )
    gateway_payment_id = models.CharField(max_length=100, null=True, blank=True)
    gateway_order_id = models.CharField(max_length=100, null=True, blank=True)
    gateway_signature = models.CharField(max_length=255, null=True, blank=True)
    gateway_response = models.JSONField(default=dict)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payment_transactions'

    def __str__(self):
        return f"{self.order_id} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.expires_at and self.status == self.PaymentStatus.INITIATED:
            # Set expiry to 30 minutes from creation for initiated payments
            self.expires_at = timezone.now() + timezone.timedelta(minutes=30)
        super().save(*args, **kwargs)
