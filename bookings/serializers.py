from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import BookingSlot, BookingOrder, BookingMember
from users.serializers import PatientSerializer, StaffMemberSerializer
from packages.serializers import PackageSerializer
from coupons.serializers import CouponSerializer
from django.core.exceptions import ValidationError
from .services import BookingService, CouponService, SlotService

class BookingSlotSerializer(serializers.ModelSerializer):
    package_details = PackageSerializer(source='package', read_only=True)
    
    class Meta:
        model = BookingSlot
        fields = '__all__'

    def validate(self, data):
        # Validate total slots
        if data.get('total_slots', 0) < 1:
            raise serializers.ValidationError({
                'total_slots': 'Total slots must be at least 1'
            })

        # Validate date is not in past
        if data.get('date'):
            if data['date'] < timezone.now().date():
                raise serializers.ValidationError({
                    'date': 'Cannot create slots for past dates'
                })

        return data

class BookingMemberSerializer(serializers.ModelSerializer):
    patient = PatientSerializer()

    class Meta:
        model = BookingMember
        fields = ['id', 'patient', 'is_primary_contact']

    def create(self, validated_data):
        # Use service layer for business logic
        patient_data = validated_data.pop('patient')
        booking = validated_data.get('booking')
        
        return BookingService.add_member_to_booking(
            booking_order=booking,
            patient_data=patient_data,
            is_primary_contact=validated_data.get('is_primary_contact', False)
        )

class BookingOrderSerializer(serializers.ModelSerializer):
    members = BookingMemberSerializer(many=True, read_only=True)
    package = PackageSerializer(read_only=True)
    online_coupon = CouponSerializer(read_only=True)
    promotional_coupon = CouponSerializer(read_only=True)
    online_coupon_code = serializers.CharField(write_only=True, required=False)
    promotional_coupon_code = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = BookingOrder
        fields = [
            'id', 'booking_slot', 'user', 'package', 'status',
            'total_amount', 'final_amount', 'is_assisted_booking',
            'number_of_members', 'members', 'online_coupon',
            'promotional_coupon', 'online_discount', 'promotional_discount',
            'online_coupon_code', 'promotional_coupon_code',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['total_amount', 'final_amount', 'user', 'package', 'status',
                           'online_discount', 'promotional_discount', 'created_at', 'modified_at']

    def validate(self, data):
        if self.instance is None:  # Only for creation
            if not data.get('booking_slot'):
                raise serializers.ValidationError("Booking slot is required")
            
            booking_slot = data['booking_slot']
            number_of_members = data.get('number_of_members', 1)
            
            # Use service layer for validation
            try:
                # Validate slot availability
                if booking_slot.available_slots < number_of_members:
                    raise serializers.ValidationError(f"Not enough slots available. Only {booking_slot.available_slots} slots left")
                
                if not booking_slot.is_active:
                    raise serializers.ValidationError("This booking slot is not active")

                # Calculate initial total amount
                total_amount = booking_slot.package.base_amount * number_of_members
                data['total_amount'] = total_amount

                # Validate coupon codes if provided using service layer
                online_code = data.get('online_coupon_code')
                promo_code = data.get('promotional_coupon_code')

                if online_code:
                    is_valid, message, _ = CouponService.validate_coupon_for_booking(
                        coupon_code=online_code,
                        total_amount=total_amount
                    )
                    if not is_valid:
                        raise serializers.ValidationError(f"Online coupon invalid: {message}")
                    data['_online_coupon_code'] = online_code

                if promo_code:
                    is_valid, message, _ = CouponService.validate_coupon_for_booking(
                        coupon_code=promo_code,
                        total_amount=total_amount
                    )
                    if not is_valid:
                        raise serializers.ValidationError(f"Promotional coupon invalid: {message}")
                    data['_promotional_coupon_code'] = promo_code
                    
            except ValidationError as e:
                raise serializers.ValidationError(str(e))
            
        return data

    def create(self, validated_data):
        # Use service layer for booking creation
        online_coupon_code = validated_data.pop('_online_coupon_code', None)
        promotional_coupon_code = validated_data.pop('_promotional_coupon_code', None)
        
        # Remove any other non-model fields
        validated_data.pop('online_coupon_code', None)
        validated_data.pop('promotional_coupon_code', None)
        
        # Use service layer for booking creation
        booking_order = BookingService.create_booking_order(
            user=validated_data.get('user'),
            booking_slot=validated_data.get('booking_slot'),
            number_of_members=validated_data.get('number_of_members', 1),
            online_coupon_code=online_coupon_code,
            promotional_coupon_code=promotional_coupon_code
        )
        
        return booking_order

class ApplyCouponSerializer(serializers.Serializer):
    coupon_code = serializers.CharField(max_length=50)

    def validate(self, data):
        booking_order = self.context['booking_order']
        coupon_code = data['coupon_code']

        try:
            discount = booking_order.apply_coupon(coupon_code)
            data['discount'] = discount
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        return data 