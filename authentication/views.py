from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
import json
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer

@csrf_exempt
def register_view(request):
    """Register a new user - Pure Django view"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            serializer = RegisterSerializer(data=data)
            if serializer.is_valid():
                user = serializer.save()
                return JsonResponse({
                    'message': 'User created successfully',
                    'user': UserSerializer(user).data
                }, status=201)
            return JsonResponse(serializer.errors, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def login_view(request):
    """Login user - Pure Django view"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            serializer = LoginSerializer(data=data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                login(request, user)
                return JsonResponse({
                    'message': 'Login successful',
                    'user': UserSerializer(user).data
                }, status=200)
            return JsonResponse(serializer.errors, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def logout_view(request):
    """Logout user - Pure Django view"""
    if request.method == 'POST':
        try:
            if request.user.is_authenticated:
                logout(request)
                return JsonResponse({'message': 'Logout successful'}, status=200)
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get current user profile"""
    return Response({
        'user': UserSerializer(request.user).data
    }, status=status.HTTP_200_OK)

@csrf_exempt
def csrf_token(request):
    """Get CSRF token for frontend"""
    from django.middleware.csrf import get_token
    return JsonResponse({
        'csrfToken': get_token(request)
    })