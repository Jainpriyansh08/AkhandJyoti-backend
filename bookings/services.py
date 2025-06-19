"""
Service layer for booking operations to reduce tight coupling.
This layer handles business logic and coordinates between different models.
"""
from typing import Optional, Tuple
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import BookingOrder, BookingSlot, BookingMember
from users.models import Patient, User
from packages.models import Package
from coupons.models import Coupon


class BookingService:
    """Service class for booking-related operations."""
    
    @staticmethod
    def create_booking_order(
        user: User,
        booking_slot: BookingSlot,
        number_of_members: int = 1,
        online_coupon_code: Optional[str] = None,
        promotional_coupon_code: Optional[str] = None
    ) -> BookingOrder:
        """
        Create a new booking order with proper validation and coupon application.
        
        Args:
            user: The user making the booking
            booking_slot: The selected booking slot
            number_of_members: Number of members for the booking
            online_coupon_code: Optional online coupon code
            promotional_coupon_code: Optional promotional coupon code
            
        Returns:
            BookingOrder: The created booking order
            
        Raises:
            ValidationError: If validation fails
        """
        with transaction.atomic():
            # Validate slot availability
            if booking_slot.available_slots < number_of_members:
                raise ValidationError(f"Not enough slots available. Only {booking_slot.available_slots} slots left")
            
            if not booking_slot.is_active:
                raise ValidationError("This booking slot is not active")
            
            # Create booking order
            booking_order = BookingOrder.objects.create(
                user=user,
                booking_slot=booking_slot,
                package=booking_slot.package,
                number_of_members=number_of_members,
                total_amount=booking_slot.package.base_amount * number_of_members,
                final_amount=booking_slot.package.base_amount * number_of_members
            )
            
            # Apply coupons if provided
            if online_coupon_code:
                booking_order.apply_coupon(online_coupon_code)
            
            if promotional_coupon_code:
                booking_order.apply_coupon(promotional_coupon_code)
            
            return booking_order
    
    @staticmethod
    def add_member_to_booking(
        booking_order: BookingOrder,
        patient_data: dict,
        is_primary_contact: bool = False
    ) -> BookingMember:
        """
        Add a member to a booking order.
        
        Args:
            booking_order: The booking order to add member to
            patient_data: Patient information dictionary
            is_primary_contact: Whether this is the primary contact
            
        Returns:
            BookingMember: The created booking member
            
        Raises:
            ValidationError: If validation fails
        """
        if booking_order.status != 'IN_PROGRESS':
            raise ValidationError("Cannot add members to a booking that is not in progress")
        
        if booking_order.members.count() >= booking_order.number_of_members:
            raise ValidationError("Maximum number of members already added")
        
        # Create patient
        patient = Patient.objects.create(**patient_data)
        
        # Create booking member
        booking_member = BookingMember.objects.create(
            booking=booking_order,
            patient=patient,
            is_primary_contact=is_primary_contact
        )
        
        return booking_member
    
    @staticmethod
    def confirm_booking(booking_order: BookingOrder) -> BookingOrder:
        """
        Confirm a booking order.
        
        Args:
            booking_order: The booking order to confirm
            
        Returns:
            BookingOrder: The confirmed booking order
            
        Raises:
            ValidationError: If confirmation fails
        """
        if booking_order.status != 'IN_PROGRESS':
            raise ValidationError("Only IN_PROGRESS bookings can be confirmed")
        
        # Check resource hold expiration (15 minutes)
        if (booking_order.resource_hold_time and 
            booking_order.resource_hold_time + timezone.timedelta(minutes=15) < timezone.now()):
            booking_order.status = 'FAILED'
            booking_order.save()
            raise ValidationError("Resource hold has expired")
        
        # Check if all required members are added
        if booking_order.members.count() != booking_order.number_of_members:
            raise ValidationError("All members must be added before confirmation")
        
        booking_order.status = 'CONFIRMED'
        booking_order.save()
        
        return booking_order
    
    @staticmethod
    def cancel_booking(booking_order: BookingOrder) -> BookingOrder:
        """
        Cancel a booking order and release slots.
        
        Args:
            booking_order: The booking order to cancel
            
        Returns:
            BookingOrder: The cancelled booking order
            
        Raises:
            ValidationError: If cancellation fails
        """
        if booking_order.status not in ['IN_PROGRESS', 'CONFIRMED']:
            raise ValidationError("Cannot cancel booking in current status")
        
        with transaction.atomic():
            # Release the held slots
            booking_slot = booking_order.booking_slot
            booking_slot.available_slots += booking_order.number_of_members
            booking_slot.save()
            
            # Update booking status
            booking_order.status = 'CANCELLED'
            booking_order.save()
        
        return booking_order


class CouponService:
    """Service class for coupon-related operations."""
    
    @staticmethod
    def validate_coupon_for_booking(
        coupon_code: str,
        total_amount: Decimal,
        booking_order: Optional[BookingOrder] = None
    ) -> Tuple[bool, str, Optional[Coupon]]:
        """
        Validate a coupon for application to a booking.
        
        Args:
            coupon_code: The coupon code to validate
            total_amount: The total amount of the booking
            booking_order: Optional existing booking order for additional validation
            
        Returns:
            Tuple[bool, str, Optional[Coupon]]: (is_valid, message, coupon_object)
        """
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
        except Coupon.DoesNotExist:
            return False, "Invalid coupon code", None
        
        # Check if coupon is valid for the amount
        is_valid, message = coupon.is_valid(amount=total_amount)
        if not is_valid:
            return False, message, coupon
        
        # Additional validation for promotional coupons
        if (coupon.coupon_type in ['PROMOTIONAL', 'BULK_BOOKING'] and 
            booking_order and booking_order.promotional_coupon):
            return False, "A promotional coupon has already been applied", coupon
        
        return True, "Coupon is valid", coupon


class SlotService:
    """Service class for slot-related operations."""
    
    @staticmethod
    def get_available_slots(
        date: Optional[str] = None,
        package_id: Optional[int] = None,
        include_holidays: bool = False,
        include_inactive: bool = False,
        future_only: bool = True
    ) -> list:
        """
        Get available booking slots with filtering.
        
        Args:
            date: Specific date filter (YYYY-MM-DD)
            package_id: Specific package filter
            include_holidays: Whether to include holiday slots
            include_inactive: Whether to include inactive slots
            future_only: Whether to only show future slots
            
        Returns:
            list: List of available booking slots
        """
        queryset = BookingSlot.objects.all()
        
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        if not include_holidays:
            queryset = queryset.filter(is_holiday=False)
        
        if future_only:
            queryset = queryset.filter(date__gte=timezone.now().date())
        
        if date:
            queryset = queryset.filter(date=date)
        
        if package_id:
            queryset = queryset.filter(package_id=package_id)
        
        return list(queryset.order_by('date', 'time')) 