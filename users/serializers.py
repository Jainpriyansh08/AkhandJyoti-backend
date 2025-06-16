from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'mobile_number', 'email', 'gender', 'age', 'is_active', 'is_staff_member', 'created_at', 'modified_at']

class RegisterOrLoginSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)

class VerifyOtpSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)
    otp_code = serializers.CharField(max_length=6) 