from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
from packages.models import Package
from coupons.models import Coupon
from bookings.models import BookingSlot
from payments.models import PaymentGateway

# Create Eye Care Package
package = Package.objects.create(
    name='Eyecare Package',
    base_amount=Decimal('2999.00'),
    discounted_amount=Decimal('2849.05'),  # 5% default discount
    discount_percentage=Decimal('5.00'),
    description='Complete eye care package including consultation and tests'
)

# Create Online Default Coupon (FIRST10)
online_coupon = Coupon.objects.create(
    code='FIRST10',
    description='10% off on your first booking',
    coupon_type='ONLINE_DEFAULT',
    discount_percentage=Decimal('10.00'),
    is_active=True,
    valid_from=timezone.now(),
    valid_until=timezone.now() + timedelta(days=365),  # Valid for 1 year
    max_uses=None  # Unlimited uses
)

# Create Promotional Coupon (PRIYANSH10)
promo_coupon = Coupon.objects.create(
    code='PRIYANSH10',
    description='Additional 10% off on your booking',
    coupon_type='PROMOTIONAL',
    discount_percentage=Decimal('10.00'),
    is_active=True,
    valid_from=timezone.now(),
    valid_until=timezone.now() + timedelta(days=30),
    max_uses=100
)

# Create Razorpay Payment Gateway
payment_gateway = PaymentGateway.objects.create(
    name='razorpay',
    is_active=True,
    config={
        'key_id': 'rzp_test_key',
        'key_secret': 'rzp_test_secret'
    }
)

# Create Booking Slots for next 7 days
start_date = timezone.now().date()
for day in range(7):
    current_date = start_date + timedelta(days=day)
    # Create slots from 9 AM to 5 PM
    for hour in range(9, 17):
        BookingSlot.objects.create(
            date=current_date,
            time=datetime.strptime(f"{hour}:00", "%H:%M").time(),
            total_slots=20,
            available_slots=20,
            package=package,
            is_active=True
        )

print("Test data setup completed successfully!")
print("\nCreated data:")
print(f"1. Package: {package.name} - ₹{package.base_amount} (5% default discount)")
print(f"2. Default Coupon: {online_coupon.code} - {online_coupon.discount_percentage}% off")
print(f"3. Promotional Coupon: {promo_coupon.code} - {promo_coupon.discount_percentage}% off")
print(f"4. Payment Gateway: {payment_gateway.name}")
print(f"5. Created {BookingSlot.objects.count()} booking slots for next 7 days") 