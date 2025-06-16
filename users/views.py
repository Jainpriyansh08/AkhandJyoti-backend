from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import User, Otp
from .serializers import RegisterOrLoginSerializer, VerifyOtpSerializer, UserSerializer
import random
from rest_framework_simplejwt.tokens import RefreshToken

# Create your views here.

class RegisterOrLoginView(APIView):
    permission_classes = []
    def post(self, request):
        serializer = RegisterOrLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile_number = serializer.validated_data['mobile_number']
        user, created = User.objects.get_or_create(mobile_number=mobile_number)
        otp_code = str(random.randint(100000, 999999))
        Otp.objects.create(user=user, otp_code=otp_code, expire_at=timezone.now() + timezone.timedelta(minutes=5))
        print(f"OTP for {mobile_number}: {otp_code}")  # Simulate SMS
        return Response({"detail": "OTP sent."}, status=200)

class VerifyOtpView(APIView):
    permission_classes = []
    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile_number = serializer.validated_data['mobile_number']
        otp_code = serializer.validated_data['otp_code']
        try:
            user = User.objects.get(mobile_number=mobile_number)
            otp = Otp.objects.filter(user=user, otp_code=otp_code, expire_at__gte=timezone.now()).last()
            if otp:
                refresh = RefreshToken.for_user(user)
                return Response({
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": UserSerializer(user).data
                }, status=200)
            else:
                return Response({"detail": "Invalid or expired OTP."}, status=400)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)
