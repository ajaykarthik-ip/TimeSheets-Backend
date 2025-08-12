from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.http import JsonResponse
import json
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, GoogleLoginSerializer

# 🔥 ADD THIS CORS DECORATOR FOR ALL VIEWS
def add_cors_headers(response, request):
    """Add CORS headers to response"""
    origin = request.headers.get('Origin')
    if origin and origin in [
        'https://time-sheets-je2h.vercel.app',
        'http://localhost:3000',
        'http://127.0.0.1:3000'
    ]:
        response["Access-Control-Allow-Origin"] = origin
    
    response["Access-Control-Allow-Credentials"] = "true"
    response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-CSRFToken, X-Requested-With"
    response["Access-Control-Max-Age"] = "86400"
    return response

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def register_view(request):
    """Register a new user - Pure Django view"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response, request)
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            serializer = RegisterSerializer(data=data)
            if serializer.is_valid():
                user = serializer.save()
                response = JsonResponse({
                    'message': 'User created successfully',
                    'user': UserSerializer(user).data
                }, status=201)
                return add_cors_headers(response, request)
            response = JsonResponse(serializer.errors, status=400)
            return add_cors_headers(response, request)
        except Exception as e:
            response = JsonResponse({'error': str(e)}, status=400)
            return add_cors_headers(response, request)
    
    response = JsonResponse({'error': 'Method not allowed'}, status=405)
    return add_cors_headers(response, request)

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def login_view(request):
    """Login user - Pure Django view"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response, request)
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            serializer = LoginSerializer(data=data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                login(request, user)
                response = JsonResponse({
                    'message': 'Login successful',
                    'user': UserSerializer(user).data
                }, status=200)
                return add_cors_headers(response, request)
            response = JsonResponse(serializer.errors, status=400)
            return add_cors_headers(response, request)
        except Exception as e:
            response = JsonResponse({'error': str(e)}, status=400)
            return add_cors_headers(response, request)
    
    response = JsonResponse({'error': 'Method not allowed'}, status=405)
    return add_cors_headers(response, request)

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def logout_view(request):
    """Logout user - Pure Django view"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response, request)
        
    if request.method == 'POST':
        try:
            if request.user.is_authenticated:
                logout(request)
                response = JsonResponse({'message': 'Logout successful'}, status=200)
                return add_cors_headers(response, request)
            response = JsonResponse({'error': 'Not authenticated'}, status=401)
            return add_cors_headers(response, request)
        except Exception as e:
            response = JsonResponse({'error': str(e)}, status=400)
            return add_cors_headers(response, request)
    
    response = JsonResponse({'error': 'Method not allowed'}, status=405)
    return add_cors_headers(response, request)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get current user profile"""
    return Response({
        'user': UserSerializer(request.user).data
    }, status=status.HTTP_200_OK)

@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def csrf_token(request):
    """Get CSRF token for frontend"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response, request)
        
    from django.middleware.csrf import get_token
    response = JsonResponse({
        'csrfToken': get_token(request)
    })
    return add_cors_headers(response, request)

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def google_login_view(request):
    """Login/Register user with Google OAuth - Pure Django view"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response, request)
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            serializer = GoogleLoginSerializer(data=data)
            
            if serializer.is_valid():
                # Get verified Google user data
                google_data = serializer.validated_data['token']
                
                # Create or get user
                user, created = serializer.create_or_get_user(google_data)
                
                # Log the user in
                login(request, user)
                
                # Determine response message
                if created:
                    message = 'Account created and logged in successfully with Google'
                else:
                    message = 'Logged in successfully with Google'
                
                response = JsonResponse({
                    'message': message,
                    'user': UserSerializer(user).data,
                    'created': created,
                    'google_data': {
                        'picture': google_data.get('picture'),
                        'email_verified': google_data.get('email_verified', False)
                    }
                }, status=200)
                return add_cors_headers(response, request)
            
            response = JsonResponse(serializer.errors, status=400)
            return add_cors_headers(response, request)
            
        except Exception as e:
            response = JsonResponse({
                'error': 'Google login failed',
                'details': str(e)
            }, status=400)
            return add_cors_headers(response, request)
    
    response = JsonResponse({'error': 'Method not allowed'}, status=405)
    return add_cors_headers(response, request)

# 🔧 CORS Test View
@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def cors_test(request):
    """Test CORS configuration - TEMPORARY DEBUG VIEW"""
    
    print(f"🧪 CORS Test: {request.method} request from {request.headers.get('Origin', 'unknown origin')}")
    
    if request.method == "OPTIONS":
        # Handle preflight request
        print("✈️ Handling preflight OPTIONS request")
        response = JsonResponse({'status': 'preflight ok'})
    else:
        # Handle actual request
        print("📡 Handling actual request")
        response = JsonResponse({
            'status': 'CORS test successful! 🎉',
            'method': request.method,
            'timestamp': str(request.META.get('HTTP_DATE', 'no date')),
            'origin': request.headers.get('Origin', 'No origin header'),
            'user_agent': request.headers.get('User-Agent', 'No user agent'),
            'cookies_received': len(request.COOKIES),
            'session_key': request.session.session_key if hasattr(request.session, 'session_key') else 'No session',
        })
    
    return add_cors_headers(response, request)