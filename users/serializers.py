from rest_framework import serializers
from .models import User, Otp, Patient, StaffMember

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'mobile_number', 'email', 'gender', 'age', 'is_active', 'is_staff_member', 'created_at', 'modified_at']
        read_only_fields = ['is_active', 'is_staff_member', 'created_at', 'modified_at']

class PatientSerializer(serializers.ModelSerializer):
    is_primary = serializers.BooleanField(default=False)

    class Meta:
        model = Patient
        fields = ['id', 'first_name', 'last_name', 'age', 'mobile_number', 'gender', 'is_primary']

    def validate_age(self, value):
        if value < 0 or value > 120:
            raise serializers.ValidationError("Age must be between 0 and 120")
        return value

    def validate_gender(self, value):
        if value not in ['M', 'F', 'O']:
            raise serializers.ValidationError("Gender must be 'M', 'F', or 'O'")
        return value

class RegisterOrLoginSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15)

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

        # Check if exactly one patient is marked as primary
        primary_count = sum(1 for patient in data['patients'] if patient.get('is_primary', False))
        if primary_count != 1:
            raise serializers.ValidationError("Exactly one patient must be marked as primary")

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
    mobile_number = serializers.CharField(write_only=True)
    
    class Meta:
        model = StaffMember
        fields = ['id', 'staff_code', 'mobile_number', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        mobile_number = validated_data.pop('mobile_number')
        user = User.objects.get(mobile_number=mobile_number)
        user.is_staff_member = True
        user.save()
        staff_member = StaffMember.objects.create(user=user, **validated_data)
        return staff_member 