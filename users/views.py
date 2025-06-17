from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import User, Otp, Patient
from .serializers import (
    RegisterOrLoginSerializer, 
    VerifyOtpSerializer, 
    UserSerializer,
    UpdateProfileSerializer,
    StaffMemberSerializer,
    PatientSerializer,
    PatientRegistrationSerializer
)
import random
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView
from django.db import transaction

# Create your views here.

class RegisterOrLoginView(APIView):
    permission_classes = []
    
    def post(self, request):
        serializer = RegisterOrLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mobile_number = serializer.validated_data['mobile_number']
        
        # Create or get user
        user, created = User.objects.get_or_create(mobile_number=mobile_number)
        
        # Generate and save OTP
        otp_code = str(random.randint(100000, 999999))
        Otp.objects.create(
            user=user,
            otp_code=otp_code,
            expire_at=timezone.now() + timezone.timedelta(minutes=5)
        )
        
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
            otp = Otp.objects.filter(
                user=user,
                otp_code=otp_code,
                expire_at__gte=timezone.now()
            ).last()
            
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

class PatientRegistrationView(APIView):
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        serializer = PatientRegistrationSerializer(
            data=request.data,
            context={'user': request.user}
        )
        serializer.is_valid(raise_exception=True)
        
        patients_data = serializer.validated_data['patients']
        
        registered_patients = []
        for patient_data in patients_data:
            is_primary = patient_data.pop('is_primary', False)
            patient, created = Patient.objects.get_or_create(
                mobile_number=patient_data['mobile_number'],
                defaults={
                    'first_name': patient_data['first_name'],
                    'last_name': patient_data['last_name'],
                    'age': patient_data['age'],
                    'gender': patient_data['gender'],
                    'is_primary': is_primary
                }
            )
            
            # If patient exists but details are different, update them
            if not created:
                for field in ['first_name', 'last_name', 'age', 'gender', 'is_primary']:
                    if field == 'is_primary':
                        setattr(patient, field, is_primary)
                    elif field in patient_data and getattr(patient, field) != patient_data[field]:
                        setattr(patient, field, patient_data[field])
                patient.save()
            
            registered_patients.append(patient)

        return Response({
            "detail": "Patients registered successfully",
            "patients": PatientSerializer(registered_patients, many=True).data
        }, status=200)

class ProfileView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateProfileSerializer

    def get_object(self):
        return self.request.user

class RegisterStaffMemberView(CreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = StaffMemberSerializer

    def perform_create(self, serializer):
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Successfully logged out."}, status=200)
        except Exception:
            return Response({"detail": "Invalid token."}, status=400)
