# Update your authentication/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate 
from django.utils import timezone
from employees.models import Employee

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password', 'password_confirm')
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)

        # ✅ Create linked Employee with new structure
        Employee.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            role='mobiux_employee',  # default role
            department='',  # default department
            designation='',  # default designation
            hire_date=timezone.now(),
        )

        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            try:
                user = User.objects.get(email=email)
                username = user.username
            except User.DoesNotExist:
                raise serializers.ValidationError('Invalid email or password')
            
            user = authenticate(username=username, password=password)
            
            if user:
                if user.is_active:
                    data['user'] = user
                else:
                    raise serializers.ValidationError('User account is disabled')
            else:
                raise serializers.ValidationError('Invalid email or password')
        else:
            raise serializers.ValidationError('Email and password are required')
        
        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)

class GoogleLoginSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, help_text="Google OAuth token")
    
    def validate_token(self, value):
        """Verify Google token and extract user data"""
        from .oauth import verify_google_token
        
        user_data = verify_google_token(value)
        if not user_data:
            raise serializers.ValidationError("Invalid Google token")
        
        if not user_data.get('email_verified'):
            raise serializers.ValidationError("Google email not verified")
        
        return user_data
    
    def create_or_get_user(self, google_data):
        """Create new user or get existing user from Google data"""
        from .oauth import generate_username_from_email, generate_secure_password
        
        email = google_data['email']
        
        try:
            user = User.objects.get(email=email)
            return user, False
        except User.DoesNotExist:
            pass
        
        username = generate_username_from_email(email)
        password = generate_secure_password()
        
        first_name = google_data.get('first_name', '')
        last_name = google_data.get('last_name', '')
        
        if not first_name and not last_name and google_data.get('full_name'):
            name_parts = google_data['full_name'].split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create linked Employee with new structure
        Employee.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role='mobiux_employee',  # default role
            department='',  # default department  
            designation='',  # default designation
            hire_date=timezone.now(),
        )
        
        return user, True