from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from .models import Coupon
from .serializers import CouponSerializer, ValidateCouponSerializer
from decimal import Decimal

# Create your views here.

class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Coupon.objects.all()

    @action(detail=False, methods=['post'], url_path='get-online-discount')
    def get_online_discount(self, request):
        """
        Get the default online discount that's applied automatically.
        Expects:
        {
            "package_id": 1,
            "amount": 23992
        }
        """
        try:
            amount = Decimal(request.data.get('amount', 0))
            if amount <= 0:
                raise ValidationError("Invalid amount")

            # Get the active ONLINE_DEFAULT coupon
            coupon = Coupon.objects.filter(
                coupon_type='ONLINE_DEFAULT',
                is_active=True
            ).first()

            if not coupon:
                return Response({
                    "status": "error",
                    "code": "no_default_coupon",
                    "message": "No default online coupon configured"
                }, status=status.HTTP_404_NOT_FOUND)

            # Calculate discount
            discount = coupon.calculate_discount(amount)
            final_amount = amount - discount

            return Response({
                "status": "success",
                "code": "default_discount_applied",
                "data": {
                    "coupon": {
                        "code": coupon.code,
                        "type": coupon.coupon_type
                    },
                    "original_amount": float(amount),
                    "discount": float(discount),
                    "final_amount": float(final_amount)
                }
            }, status=status.HTTP_200_OK)

        except (ValueError, ValidationError) as e:
            return Response({
                "status": "error",
                "code": "invalid_request",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='validate-promotional')
    def validate_promotional(self, request):
        """
        Validate a promotional coupon code.
        Expects:
        {
            "code": "PROMO123",
            "amount": 23992,
            "package_id": 1
        }
        """
        try:
            code = request.data.get('code')
            amount = Decimal(request.data.get('amount', 0))

            if not code:
                raise ValidationError("Coupon code is required")
            if amount <= 0:
                raise ValidationError("Invalid amount")

            # Get the promotional coupon
            try:
                coupon = Coupon.objects.get(
                    code=code,
                    is_active=True,
                    coupon_type__in=['PROMOTIONAL', 'BULK_BOOKING']
                )
            except Coupon.DoesNotExist:
                return Response({
                    "status": "error",
                    "code": "invalid_coupon",
                    "message": "Invalid or expired coupon code"
                }, status=status.HTTP_404_NOT_FOUND)

            # Validate usage limits
            if coupon.max_uses and coupon.current_uses >= coupon.max_uses:
                return Response({
                    "status": "error",
                    "code": "coupon_exhausted",
                    "message": "This coupon has reached its usage limit"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate discount
            discount = coupon.calculate_discount(amount)
            final_amount = amount - discount

            return Response({
                "status": "success",
                "code": "promotional_valid",
                "data": {
                    "coupon": {
                        "code": coupon.code,
                        "type": coupon.coupon_type
                    },
                    "original_amount": float(amount),
                    "discount": float(discount),
                    "final_amount": float(final_amount)
                }
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response({
                "status": "error",
                "code": "validation_error",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "status": "error",
                "code": "server_error",
                "message": "An error occurred while processing the coupon"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
