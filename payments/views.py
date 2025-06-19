from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
import json
import logging
from .services import PaymentService
from bookings.models import BookingOrder
from .models import PaymentTransaction

logger = logging.getLogger(__name__)

# Create your views here.

class InitiatePaymentView(APIView):
    """View to initiate payment for a booking order"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Initiate payment for a booking order
        
        Expected payload:
        {
            "booking_id": 123
        }
        """
        booking_id = request.data.get('booking_id')
        if not booking_id:
            return Response(
                {'error': 'booking_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            booking_order = BookingOrder.objects.get(id=booking_id, user=request.user)
            
            # Create payment order
            result = PaymentService.create_payment_order(booking_order)
            
            if not result['success']:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(result['data'])

        except BookingOrder.DoesNotExist:
            return Response(
                {'error': 'Booking order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error initiating payment for booking {booking_id}: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PaymentStatusView(APIView):
    """View to check payment status"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Get payment status for a given order ID
        
        Query params:
        - order_id: Razorpay order ID
        """
        order_id = request.query_params.get('order_id')
        if not order_id:
            return Response(
                {'error': 'order_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = PaymentService.get_payment_status(order_id)
            
            if not result['success']:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(result['data'])

        except Exception as e:
            logger.error(f"Error getting payment status for order {order_id}: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(APIView):
    """View to handle Razorpay webhooks"""
    
    def post(self, request, *args, **kwargs):
        """
        Handle Razorpay webhook
        
        Expected payload from Razorpay:
        {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_xxx",
                        "order_id": "order_xxx",
                        "status": "captured"
                    }
                }
            }
        }
        """
        try:
            # Get webhook payload
            webhook_data = json.loads(request.body)
            event = webhook_data.get('event')
            
            logger.info(f"Received Razorpay webhook: {event}")
            
            # Handle payment.captured event
            if event == 'payment.captured':
                payment_data = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
                
                payment_id = payment_data.get('id')
                order_id = payment_data.get('order_id')
                
                if not payment_id or not order_id:
                    logger.error("Missing payment_id or order_id in webhook payload")
                    return HttpResponse(status=400)
                
                # Verify and process payment
                result = PaymentService.verify_payment_webhook(
                    payment_id=payment_id,
                    order_id=order_id,
                    signature=request.headers.get('X-Razorpay-Signature', '')
                )
                
                if not result['success']:
                    logger.error(f"Payment verification failed: {result['error']}")
                    return HttpResponse(status=400)
                
                logger.info(f"Payment webhook processed successfully: {result['data']}")
                return HttpResponse(status=200)
            
            # Handle other events if needed
            elif event == 'payment.failed':
                # Handle failed payment
                logger.info(f"Payment failed webhook received: {webhook_data}")
                return HttpResponse(status=200)
            
            else:
                logger.info(f"Unhandled webhook event: {event}")
                return HttpResponse(status=200)

        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return HttpResponse(status=400)
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return HttpResponse(status=500)

class PaymentHistoryView(APIView):
    """View to get payment history for a user"""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Get payment history for the authenticated user
        """
        try:
            # Get all booking orders for the user with payment transactions
            booking_orders = BookingOrder.objects.filter(
                user=request.user,
                payment_transaction__isnull=False
            ).select_related('payment_transaction', 'package').prefetch_related('members')

            payment_history = []
            for booking in booking_orders:
                payment = booking.payment_transaction
                payment_history.append({
                    'booking_id': booking.id,
                    'order_id': payment.order_id,
                    'amount': payment.amount,
                    'currency': payment.currency,
                    'status': payment.status,
                    'package_name': booking.package.name,
                    'number_of_members': booking.number_of_members,
                    'created_at': payment.created_at,
                    'updated_at': payment.updated_at,
                    'gateway_payment_id': payment.gateway_payment_id
                })

            return Response({
                'success': True,
                'data': payment_history
            })

        except Exception as e:
            logger.error(f"Error getting payment history for user {request.user.id}: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
