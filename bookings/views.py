from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from .models import BookingSlot, BookingOrder, BookingMember
from .serializers import (
    BookingSlotSerializer,
    BookingOrderSerializer,
    BookingMemberSerializer,
    ApplyCouponSerializer
)
from .services import BookingService, SlotService
from django.core.exceptions import ValidationError

# Create your views here.

class IsStaffMemberOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff_member

class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow staff members to create/edit slots.
    """
    def has_permission(self, request, view):
        # Allow read-only access for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        # Write permissions only for staff
        return request.user and (request.user.is_staff or request.user.is_staff_member)

class BookingSlotViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing booking slots.
    """
    queryset = BookingSlot.objects.all()
    serializer_class = BookingSlotSerializer
    
    def get_permissions(self):
        """
        Allow unauthenticated access to list and retrieve.
        Require staff permissions for create, update, delete.
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
            self.authentication_classes = []  # No authentication required for list and retrieve
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """
        Use service layer for slot filtering logic.
        """
        # Get query parameters
        date = self.request.query_params.get('date')
        package_id = self.request.query_params.get('package_id')
        include_holidays = self.request.query_params.get('include_holidays', 'false').lower() == 'true'
        include_inactive = self.request.query_params.get('include_inactive', 'false').lower() == 'true'
        future_only = self.request.query_params.get('future_only', 'true').lower() == 'true'

        # Use service layer for filtering
        slots = SlotService.get_available_slots(
            date=date,
            package_id=package_id,
            include_holidays=include_holidays,
            include_inactive=include_inactive,
            future_only=future_only
        )
        
        # Convert back to queryset for DRF
        slot_ids = [slot.id for slot in slots]
        return BookingSlot.objects.filter(id__in=slot_ids).order_by('date', 'time')

    def perform_create(self, serializer):
        """
        Set available_slots equal to total_slots when creating.
        """
        serializer.save(available_slots=serializer.validated_data['total_slots'])

class BookingOrderViewSet(viewsets.ModelViewSet):
    queryset = BookingOrder.objects.all()
    serializer_class = BookingOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BookingOrder.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        booking_slot = serializer.validated_data['booking_slot']
        serializer.save(
            user=self.request.user,
            package=booking_slot.package
        )

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        
        try:
            # Use service layer for confirmation logic
            updated_booking = BookingService.confirm_booking(booking)
            return Response(self.get_serializer(updated_booking).data)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        booking = self.get_object()
        
        if booking.status != 'CONFIRMED':
            return Response(
                {"detail": "Only CONFIRMED bookings can be completed"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = 'COMPLETED'
        booking.save()
        
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        
        try:
            # Use service layer for cancellation logic
            updated_booking = BookingService.cancel_booking(booking)
            return Response(self.get_serializer(updated_booking).data)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        booking_order = self.get_object()
        
        serializer = BookingMemberSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Use service layer for member addition
                booking_member = BookingService.add_member_to_booking(
                    booking_order=booking_order,
                    patient_data=serializer.validated_data['patient'],
                    is_primary_contact=serializer.validated_data.get('is_primary_contact', False)
                )
                return Response(BookingMemberSerializer(booking_member).data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def apply_coupon(self, request, pk=None):
        booking_order = self.get_object()
        
        if booking_order.status != 'IN_PROGRESS':
            return Response(
                {"detail": "Cannot apply coupon to a booking that is not in progress"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ApplyCouponSerializer(
            data=request.data,
            context={'booking_order': booking_order}
        )
        
        if serializer.is_valid():
            return Response({
                'discount_applied': serializer.validated_data['discount'],
                'final_amount': booking_order.final_amount
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_coupon(self, request, pk=None):
        booking_order = self.get_object()
        
        if booking_order.status != 'IN_PROGRESS':
            return Response(
                {"detail": "Cannot remove coupon from a booking that is not in progress"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        coupon_code = request.data.get('coupon_code')
        if not coupon_code:
            return Response(
                {"detail": "Coupon code is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            discount_removed = booking_order.remove_coupon(coupon_code)
            return Response({
                'discount_removed': discount_removed,
                'final_amount': booking_order.final_amount
            })
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def make_payment(self, request, pk=None):
        booking_order = self.get_object()
        
        if booking_order.status != 'IN_PROGRESS':
            return Response(
                {"detail": "Cannot process payment for a booking that is not in progress"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if booking_order.members.count() != booking_order.number_of_members:
            return Response(
                {"detail": "Please add all members before making payment"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Here you would integrate with your payment gateway
        # For now, we'll just mark the booking as confirmed
        booking_order.status = 'CONFIRMED'
        booking_order.save()
        
        serializer = self.get_serializer(booking_order)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        bookings = self.get_queryset().filter(
            user=request.user
        ).order_by('-created_at')
        page = self.paginate_queryset(bookings)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
