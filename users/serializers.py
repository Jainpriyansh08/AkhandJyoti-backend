from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import User, Otp, Patient, StaffMember

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'mobile_number', 'email', 'gender', 'age', 'is_active', 'is_staff_member', 'created_at', 'modified_at']
        read_only_fields = ['created_at', 'modified_at']

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'first_name', 'last_name', 'age', 'mobile_number', 'gender']
        read_only_fields = ['id']

class PatientListSerializer(serializers.Serializer):
    total_patients = serializers.IntegerField()
    user_is_patient = serializers.BooleanField()
    patients = serializers.ListField(child=PatientSerializer())

    def validate(self, data):
        if data['total_patients'] != len(data['patients']):
            raise serializers.ValidationError("Total patients count doesn't match with provided patients")
        return data

class RegisterOrLoginSerializer(serializers.Serializer):
    mobile_number = serializers.CharField()

class VerifyOtpSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)
    otp_code = serializers.CharField(max_length=6) 

class PatientRegistrationSerializer(serializers.Serializer):
    total_patients = serializers.IntegerField(min_value=1, required=True)
    patients = PatientSerializer(many=True, required=True)
    user_is_patient = serializers.BooleanField(required=True, help_text="Whether the logged-in user is one of the patients")

    def validate(self, data):
        if data['total_patients'] != len(data['patients']):
            raise serializers.ValidationError("Number of patients must match total_patients")
        
        # Check if all mobile numbers are unique
        mobile_numbers = [patient['mobile_number'] for patient in data['patients']]
        if len(set(mobile_numbers)) != len(mobile_numbers):
            raise serializers.ValidationError("Each patient must have a unique mobile number")

        # If user_is_patient is True, verify that one of the patients has the same mobile number
        if data['user_is_patient']:
            user_mobile = self.context['user'].mobile_number
            if user_mobile not in mobile_numbers:
                raise serializers.ValidationError("When user is a patient, their mobile number must be included in patients list")

        return data

class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'gender', 'age']
        
    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

class StaffMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = StaffMember
        fields = ['id', 'user', 'department', 'designation', 'created_at', 'modified_at']
        read_only_fields = ['created_at', 'modified_at']

    def create(self, validated_data):
        mobile_number = validated_data.pop('mobile_number')
        user = User.objects.get(mobile_number=mobile_number)
        user.is_staff_member = True
        user.save()
        staff_member = StaffMember.objects.create(user=user, **validated_data)
        return staff_member 

class OtpSerializer(serializers.ModelSerializer):
    class Meta:
        model = Otp
        fields = ['mobile_number', 'otp_code']

class OtpVerificationSerializer(serializers.Serializer):
    mobile_number = serializers.CharField()
    otp_code = serializers.CharField() 