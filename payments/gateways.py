from abc import ABC, abstractmethod
from typing import Dict, Any
import razorpay
from django.conf import settings

class PaymentGatewayStrategy(ABC):
    """Abstract base class for payment gateway implementations"""

    @abstractmethod
    def create_order(self, amount: int, currency: str, **kwargs) -> Dict[str, Any]:
        """Create a payment order"""
        pass

    @abstractmethod
    def verify_payment(self, payment_id: str, order_id: str, signature: str, **kwargs) -> bool:
        """Verify payment signature"""
        pass

    @abstractmethod
    def get_payment_status(self, payment_id: str) -> str:
        """Get payment status from gateway"""
        pass

class RazorpayGateway(PaymentGatewayStrategy):
    """Razorpay payment gateway implementation"""

    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    def create_order(self, amount: int, currency: str, **kwargs) -> Dict[str, Any]:
        """
        Create a Razorpay order
        Amount should be in smallest currency unit (paise for INR)
        """
        try:
            order_data = {
                'amount': amount,
                'currency': currency,
                'receipt': kwargs.get('receipt'),
                'notes': kwargs.get('notes', {})
            }
            order = self.client.order.create(data=order_data)
            return {
                'success': True,
                'data': order
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def verify_payment(self, payment_id: str, order_id: str, signature: str, **kwargs) -> bool:
        """Verify Razorpay payment signature"""
        try:
            params_dict = {
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': order_id,
                'razorpay_signature': signature
            }
            self.client.utility.verify_payment_signature(params_dict)
            return True
        except Exception:
            return False

    def get_payment_status(self, payment_id: str) -> str:
        """Get payment status from Razorpay"""
        try:
            payment = self.client.payment.fetch(payment_id)
            return payment.get('status', 'unknown')
        except Exception:
            return 'error'

class PaymentGatewayFactory:
    """Factory class to get payment gateway instance"""
    
    @staticmethod
    def get_gateway(gateway_name: str) -> PaymentGatewayStrategy:
        gateways = {
            'razorpay': RazorpayGateway,
            # Add more gateways here as needed
        }
        
        gateway_class = gateways.get(gateway_name.lower())
        if not gateway_class:
            raise ValueError(f"Unsupported payment gateway: {gateway_name}")
            
        return gateway_class() 