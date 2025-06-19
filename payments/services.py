from decimal import Decimal
from typing import Dict, Any, Optional
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from .models import PaymentTransaction, PaymentGateway
from .gateways import PaymentGatewayFactory
from bookings.models import BookingOrder
import logging

logger = logging.getLogger(__name__)

class PaymentService:
    """Service class to handle payment-related operations"""

    @staticmethod
    def _convert_to_paisa(amount: Decimal) -> int:
        """Convert rupees to paisa"""
        return int(amount * 100)

    @staticmethod
    def _convert_to_rupees(amount: int) -> Decimal:
        """Convert paisa to rupees"""
        return Decimal(amount) / 100

    @classmethod
    def create_payment_order(cls, booking_order: BookingOrder, gateway_name: str = 'razorpay') -> Dict[str, Any]:
        """
        Create a payment order for a booking
        
        Args:
            booking_order: The booking order to create payment for
            gateway_name: Name of the payment gateway to use
            
        Returns:
            Dict containing success status and payment details or error message
        """
        try:
            # Validate booking order
            if booking_order.status not in ['IN_PROGRESS', 'CONFIRMED']:
                return {
                    'success': False,
                    'error': 'Booking must be in progress or confirmed to initiate payment'
                }

            # Check if payment already exists
            if booking_order.payment_transaction:
                if booking_order.payment_transaction.status == PaymentTransaction.PaymentStatus.SUCCESS:
                    return {
                        'success': False,
                        'error': 'Payment already completed for this booking'
                    }
                elif booking_order.payment_transaction.status == PaymentTransaction.PaymentStatus.INITIATED:
                    # Return existing payment details
                    return {
                        'success': True,
                        'data': {
                            'order_id': booking_order.payment_transaction.order_id,
                            'amount': cls._convert_to_paisa(booking_order.payment_transaction.amount),
                            'currency': booking_order.payment_transaction.currency,
                            'key': settings.RAZORPAY_KEY_ID,
                            'prefill': {
                                'name': booking_order.user.first_name or booking_order.user.mobile_number,
                                'contact': booking_order.user.mobile_number,
                                'email': booking_order.user.email or f"{booking_order.user.mobile_number}@example.com"
                            }
                        }
                    }

            # Get payment gateway
            try:
                gateway_obj = PaymentGateway.objects.get(name=gateway_name, is_active=True)
            except PaymentGateway.DoesNotExist:
                return {
                    'success': False,
                    'error': f'Payment gateway {gateway_name} not configured or inactive'
                }

            gateway = PaymentGatewayFactory.get_gateway(gateway_name)

            # Create order with gateway
            amount_in_paisa = cls._convert_to_paisa(booking_order.final_amount)
            
            # Prepare customer details
            customer_name = booking_order.user.first_name or booking_order.user.mobile_number
            customer_phone = booking_order.user.mobile_number
            customer_email = booking_order.user.email or f"{customer_phone}@example.com"
            
            gateway_response = gateway.create_order(
                amount=amount_in_paisa,
                currency=settings.PAYMENT_CURRENCY,
                receipt=f"booking_{booking_order.id}",
                notes={
                    'booking_id': str(booking_order.id),
                    'customer_name': customer_name,
                    'customer_phone': customer_phone,
                    'customer_email': customer_email,
                    'package_name': booking_order.package.name,
                    'number_of_members': booking_order.number_of_members
                }
            )

            if not gateway_response['success']:
                logger.error(f"Gateway order creation failed: {gateway_response.get('error')}")
                return {
                    'success': False,
                    'error': gateway_response.get('error', 'Failed to create payment order')
                }

            # Create payment transaction
            with transaction.atomic():
                payment = PaymentTransaction.objects.create(
                    order_id=gateway_response['data']['id'],
                    payment_gateway=gateway_obj,
                    amount=booking_order.final_amount,
                    currency=settings.PAYMENT_CURRENCY,
                    gateway_response=gateway_response['data'],
                    status=PaymentTransaction.PaymentStatus.INITIATED
                )

                # Update booking order with payment details
                booking_order.payment_transaction = payment
                booking_order.save()

            logger.info(f"Payment order created successfully for booking {booking_order.id}: {payment.order_id}")

            return {
                'success': True,
                'data': {
                    'order_id': payment.order_id,
                    'amount': amount_in_paisa,
                    'currency': payment.currency,
                    'key': settings.RAZORPAY_KEY_ID,
                    'prefill': {
                        'name': customer_name,
                        'contact': customer_phone,
                        'email': customer_email
                    },
                    'notes': {
                        'booking_id': str(booking_order.id),
                        'package_name': booking_order.package.name
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error creating payment order for booking {booking_order.id}: {str(e)}")
            return {
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }

    @classmethod
    def verify_payment_webhook(cls, payment_id: str, order_id: str, signature: str) -> Dict[str, Any]:
        """
        Verify payment webhook from gateway and update transaction status
        
        Args:
            payment_id: Payment ID from gateway
            order_id: Order ID from gateway
            signature: Payment signature for verification
            
        Returns:
            Dict containing success status and updated payment details
        """
        try:
            # Get payment transaction
            try:
                payment = PaymentTransaction.objects.select_related('payment_gateway').get(order_id=order_id)
            except PaymentTransaction.DoesNotExist:
                logger.error(f"Payment transaction not found for order_id: {order_id}")
                return {
                    'success': False,
                    'error': 'Payment order not found'
                }

            # Check if payment already processed
            if payment.status == PaymentTransaction.PaymentStatus.SUCCESS:
                return {
                    'success': True,
                    'data': {
                        'status': payment.status,
                        'order_id': payment.order_id,
                        'message': 'Payment already processed'
                    }
                }

            gateway = PaymentGatewayFactory.get_gateway(payment.payment_gateway.name)

            # Verify signature
            is_valid = gateway.verify_payment(payment_id, order_id, signature)
            if not is_valid:
                logger.error(f"Invalid payment signature for order_id: {order_id}")
                return {
                    'success': False,
                    'error': 'Invalid payment signature'
                }

            # Get payment status from gateway
            gateway_status = gateway.get_payment_status(payment_id)

            with transaction.atomic():
                # Update payment transaction
                payment.gateway_payment_id = payment_id
                payment.gateway_signature = signature
                
                if gateway_status == 'captured':
                    payment.status = PaymentTransaction.PaymentStatus.SUCCESS
                elif gateway_status in ['failed', 'cancelled']:
                    payment.status = PaymentTransaction.PaymentStatus.FAILED
                    payment.error_message = f"Payment {gateway_status} by gateway"
                else:
                    payment.status = PaymentTransaction.PaymentStatus.PROCESSING
                
                payment.save()

                # Update booking order status if payment successful
                if payment.status == PaymentTransaction.PaymentStatus.SUCCESS:
                    booking_orders = payment.booking_orders.all()
                    for booking_order in booking_orders:
                        if booking_order.status in ['IN_PROGRESS', 'CONFIRMED']:
                            booking_order.status = 'CONFIRMED'
                            booking_order.save()
                            logger.info(f"Booking {booking_order.id} confirmed after successful payment")

            logger.info(f"Payment webhook processed successfully for order_id: {order_id}, status: {payment.status}")

            return {
                'success': True,
                'data': {
                    'status': payment.status,
                    'order_id': payment.order_id,
                    'payment_id': payment_id,
                    'booking_ids': [bo.id for bo in payment.booking_orders.all()]
                }
            }

        except Exception as e:
            logger.error(f"Error processing payment webhook for order_id {order_id}: {str(e)}")
            return {
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }

    @classmethod
    def get_payment_status(cls, order_id: str) -> Dict[str, Any]:
        """
        Get payment status for a given order ID
        
        Args:
            order_id: The order ID to check
            
        Returns:
            Dict containing payment status and details
        """
        try:
            payment = PaymentTransaction.objects.select_related('payment_gateway').get(order_id=order_id)
            
            return {
                'success': True,
                'data': {
                    'order_id': payment.order_id,
                    'status': payment.status,
                    'amount': payment.amount,
                    'currency': payment.currency,
                    'created_at': payment.created_at,
                    'updated_at': payment.updated_at,
                    'gateway_payment_id': payment.gateway_payment_id,
                    'error_message': payment.error_message
                }
            }
        except PaymentTransaction.DoesNotExist:
            return {
                'success': False,
                'error': 'Payment order not found'
            }
        except Exception as e:
            logger.error(f"Error getting payment status for order_id {order_id}: {str(e)}")
            return {
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }

    @classmethod
    def handle_idle_payments(cls, idle_minutes: int = None) -> Dict[str, Any]:
        """
        Mark payments as failed if they have been in idle state for too long
        
        Args:
            idle_minutes: Minutes after which to mark payments as idle (defaults to settings)
            
        Returns:
            Dict containing the number of payments updated
        """
        if idle_minutes is None:
            idle_minutes = settings.PAYMENT_TIMEOUT_MINUTES
            
        idle_threshold = timezone.now() - timezone.timedelta(minutes=idle_minutes)
        
        updated_count = PaymentTransaction.objects.filter(
            status=PaymentTransaction.PaymentStatus.INITIATED,
            created_at__lt=idle_threshold
        ).update(
            status=PaymentTransaction.PaymentStatus.FAILED,
            error_message='Payment timeout - no response received within time limit'
        )
        
        logger.info(f"Marked {updated_count} idle payments as failed")
        
        return {
            'success': True,
            'data': {
                'updated_count': updated_count,
                'idle_minutes': idle_minutes
            }
        } 