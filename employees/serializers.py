from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Employee

class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    manager_name = serializers.SerializerMethodField()
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'username', 'password', 'first_name', 'last_name', 
            'email', 'phone', 'role', 'department', 'hire_date', 'is_active', 
            'hourly_rate', 'manager', 'manager_name', 'address', 'emergency_contact_name', 
            'emergency_contact_phone', 'full_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'full_name', 'manager_name']
    
    def get_manager_name(self, obj):
        return obj.manager.full_name if obj.manager else None
    
    def create(self, validated_data):
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        
        # Create user account
        user = User.objects.create_user(
            username=username,
            email=validated_data['email'],
            password=password,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        
        # Create employee
        employee = Employee.objects.create(user=user, **validated_data)
        return employee
    
    def update(self, instance, validated_data):
        # Handle user update if username/password provided
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        
        if username or password:
            user = instance.user
            if username:
                user.username = username
            if password:
                user.set_password(password)
            # Update user's name and email
            user.first_name = validated_data.get('first_name', instance.first_name)
            user.last_name = validated_data.get('last_name', instance.last_name)
            user.email = validated_data.get('email', instance.email)
            user.save()
        
        # Update employee
        return super().update(instance, validated_data)

class EmployeeListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    full_name = serializers.ReadOnlyField()
    manager_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'full_name', 'email', 'role', 
            'department', 'manager_name', 'is_active', 'hire_date'
        ]
    
    def get_manager_name(self, obj):
        return obj.manager.full_name if obj.manager else None