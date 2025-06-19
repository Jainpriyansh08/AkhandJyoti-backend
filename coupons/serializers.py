from rest_framework import serializers
from .models import Coupon

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'coupon_type', 'discount_amount',
            'discount_percentage', 'description', 'is_active',
            'valid_from', 'valid_until', 'max_uses', 'current_uses',
            'min_order_amount', 'max_discount_amount'
        ]
        read_only_fields = ['current_uses']

class ValidateCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate(self, data):
        try:
            coupon = Coupon.objects.get(code=data['code'], is_active=True)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Invalid coupon code")

        # First check basic validity
        is_valid, message = coupon.is_valid()
        if not is_valid:
            raise serializers.ValidationError(message)

        # Then check amount-specific conditions
        if data['order_amount'] < coupon.min_order_amount:
            raise serializers.ValidationError(f"Order amount must be at least {coupon.min_order_amount}")

        # Calculate discount
        discount = coupon.calculate_discount(data['order_amount'])
        final_amount = float(data['order_amount']) - float(discount)

        # Add calculated values to validated data
        data['coupon'] = coupon
        data['discount'] = discount
        data['final_amount'] = final_amount

        return data 