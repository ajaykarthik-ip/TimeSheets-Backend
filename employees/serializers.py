from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Employee

class EmployeeSerializer(serializers.ModelSerializer):
    """Full serializer for detail views and create/update operations"""
    full_name = serializers.ReadOnlyField()
    manager_name = serializers.SerializerMethodField()
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'username', 'password', 'first_name', 'last_name', 
            'email', 'phone', 'role', 'department', 'designation',  # Added designation
            'hire_date', 'is_active', 'hourly_rate', 'manager', 'manager_name', 
            'address', 'emergency_contact_name', 'emergency_contact_phone', 
            'full_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'full_name', 'manager_name']
    
    def get_manager_name(self, obj):
        """Optimized manager name retrieval"""
        if obj.manager_id:
            return obj.manager.full_name if obj.manager else None
        return None
    
    def create(self, validated_data):
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        
        if not username:
            username = validated_data['email'].split('@')[0]
        
        # Create user account
        user = User.objects.create_user(
            username=username,
            email=validated_data['email'],
            password=password or 'temppass123',
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
            user.first_name = validated_data.get('first_name', instance.first_name)
            user.last_name = validated_data.get('last_name', instance.last_name)
            user.email = validated_data.get('email', instance.email)
            user.save()
        
        return super().update(instance, validated_data)

class EmployeeListSerializer(serializers.ModelSerializer):
    """Optimized serializer for list views - only essential fields"""
    full_name = serializers.ReadOnlyField()
    manager_name = serializers.CharField(source='manager.full_name', read_only=True)
    department_display = serializers.CharField(source='get_department_display', read_only=True)
    designation_display = serializers.CharField(source='get_designation_display', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'full_name', 'email', 'role', 'role_display',
            'department', 'department_display', 'designation', 'designation_display',
            'manager_name', 'is_active', 'hire_date'
        ]

class EmployeeMinimalSerializer(serializers.ModelSerializer):
    """Ultra-minimal serializer for dropdowns and quick lookups"""
    full_name = serializers.ReadOnlyField()
    designation_display = serializers.CharField(source='get_designation_display', read_only=True)
    
    class Meta:
        model = Employee
        fields = ['id', 'employee_id', 'full_name', 'role', 'designation_display', 'is_active']

class ManagerListSerializer(serializers.ModelSerializer):
    """Serializer for manager dropdown lists (admin role only)"""
    full_name = serializers.ReadOnlyField()
    designation_display = serializers.CharField(source='get_designation_display', read_only=True)
    
    class Meta:
        model = Employee
        fields = ['id', 'employee_id', 'full_name', 'designation_display']

class EmployeeStatsSerializer(serializers.Serializer):
    """Serializer for employee statistics"""
    total_employees = serializers.IntegerField()
    active_employees = serializers.IntegerField()
    by_department = serializers.DictField()
    by_role = serializers.DictField()
    by_designation = serializers.DictField()  # Added designation stats
    recent_hires = serializers.IntegerField()