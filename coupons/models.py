from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone

class Coupon(models.Model):
    COUPON_TYPES = (
        ('ONLINE_DEFAULT', 'Online Default'),
        ('PROMOTIONAL', 'Promotional'),
        ('BULK_BOOKING', 'Bulk Booking'),
    )

    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPES)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    max_uses = models.IntegerField(
        null=True, 
        blank=True,
        help_text='Maximum number of times this coupon can be used in total. Null means unlimited.'
    )
    current_uses = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'coupons'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.get_coupon_type_display()})"

    def calculate_discount(self, amount):
        """
        Calculate the discount amount based on coupon type and rules
        """
        amount = Decimal(str(amount))
        
        # Check minimum order amount
        if amount < self.min_order_amount:
            return Decimal('0')

        # Calculate base discount
        if self.discount_percentage:
            discount = (amount * self.discount_percentage) / Decimal('100')
        elif self.discount_amount:
            discount = self.discount_amount
        else:
            return Decimal('0')

        # Apply maximum discount limit if set
        if self.max_discount_amount and discount > self.max_discount_amount:
            discount = self.max_discount_amount

        return discount

    def is_valid(self, amount=None):
        """
        Check if the coupon is currently valid and can be applied to the given amount
        Returns a tuple of (is_valid: bool, message: str)
        """
        now = timezone.now()

        if not self.is_active:
            return False, "Coupon is not active"

        if self.valid_from and now < self.valid_from:
            return False, "Coupon is not yet valid"

        if self.valid_until and now > self.valid_until:
            return False, "Coupon has expired"

        if self.max_uses and self.current_uses >= self.max_uses:
            return False, "Coupon usage limit reached"
        
        if amount is not None and amount < self.min_order_amount:
            return False, f"Order amount must be at least {self.min_order_amount}"

        return True, "Coupon is valid"
