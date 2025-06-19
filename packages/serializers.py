from rest_framework import serializers
from .models import Package

class PackageSerializer(serializers.ModelSerializer):
    savings_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = Package
        fields = [
            'id', 'name', 'base_amount', 'discounted_amount', 
            'discount_percentage', 'description', 'is_active',
            'savings_amount', 'created_at', 'modified_at'
        ]
        read_only_fields = ['created_at', 'modified_at']
    
    def get_savings_amount(self, obj):
        return float(obj.base_amount) - float(obj.discounted_amount) 