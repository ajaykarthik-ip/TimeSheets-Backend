from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.core.cache import cache
import json
from .models import Employee
from .serializers import (
    EmployeeSerializer, EmployeeListSerializer
)

@csrf_exempt
def employee_list_create(request):
    """
    GET: List all employees with optimized queries and pagination
    POST: Create new employee
    TEMPORARILY REMOVED AUTHENTICATION FOR TESTING
    """
    # TEMPORARILY COMMENTED OUT FOR TESTING
    # if not request.user.is_authenticated:
    #     return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method == 'GET':
        # Optimized base queryset with select_related and prefetch_related
        employees = Employee.objects.select_related(
            'manager',  # Single foreign key - use select_related
            'user'      # One-to-one relationship
        ).prefetch_related(
            # Prefetch subordinates if needed for manager hierarchy
            Prefetch(
                'subordinates', 
                queryset=Employee.objects.select_related('user').only(
                    'id', 'employee_id', 'first_name', 'last_name', 'user__username'
                )
            )
        ).only(
            # Only fetch needed fields for better performance
            'id', 'employee_id', 'first_name', 'last_name', 'email', 
            'role', 'department', 'hire_date', 'is_active', 'manager_id',
            'manager__first_name', 'manager__last_name', 'user__username'
        )
        
        # Apply filters
        department = request.GET.get('department')
        if department:
            employees = employees.filter(department=department)
        
        role = request.GET.get('role')
        if role:
            employees = employees.filter(role=role)
        
        is_active = request.GET.get('is_active')
        if is_active is not None:
            employees = employees.filter(is_active=is_active.lower() == 'true')
        
        # Search functionality
        search = request.GET.get('search')
        if search:
            employees = employees.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Pagination - always paginate for performance
        page_size = min(int(request.GET.get('page_size', 20)), 100)  # Max 100 per page
        page = int(request.GET.get('page', 1))
        
        paginator = Paginator(employees, page_size)
        page_obj = paginator.get_page(page)
        
        # Use lightweight serializer for list view
        serializer = EmployeeListSerializer(page_obj.object_list, many=True)
        
        return JsonResponse({
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page,
            'page_size': page_size,
            'employees': serializer.data,
            'filters_applied': {
                'department': department,
                'role': role,
                'is_active': is_active,
                'search': search
            },
            'message': 'AUTHENTICATION TEMPORARILY DISABLED FOR TESTING'
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            serializer = EmployeeSerializer(data=data)
            if serializer.is_valid():
                try:
                    with transaction.atomic():
                        employee = serializer.save()
                    return JsonResponse({
                        'message': 'Employee created successfully',
                        'employee': EmployeeSerializer(employee).data
                    }, status=201)
                except Exception as e:
                    return JsonResponse({
                        'error': 'Failed to create employee',
                        'details': str(e)
                    }, status=400)
            return JsonResponse(serializer.errors, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def employee_detail(request, pk):
    """
    GET: Retrieve employee by ID with optimized queries
    PUT: Update employee
    DELETE: Delete employee
    TEMPORARILY REMOVED AUTHENTICATION FOR TESTING
    """
    # TEMPORARILY COMMENTED OUT FOR TESTING
    # if not request.user.is_authenticated:
    #     return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Optimized single object retrieval
    try:
        employee = Employee.objects.select_related(
            'manager', 'user'
        ).prefetch_related(
            'subordinates__user'
        ).get(pk=pk)
    except Employee.DoesNotExist:
        return JsonResponse({'error': 'Employee not found'}, status=404)
    
    if request.method == 'GET':
        serializer = EmployeeSerializer(employee)
        return JsonResponse({
            'employee': serializer.data
        })
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            serializer = EmployeeSerializer(employee, data=data, partial=True)
            if serializer.is_valid():
                try:
                    with transaction.atomic():
                        employee = serializer.save()
                    return JsonResponse({
                        'message': 'Employee updated successfully',
                        'employee': EmployeeSerializer(employee).data
                    })
                except Exception as e:
                    return JsonResponse({
                        'error': 'Failed to update employee',
                        'details': str(e)
                    }, status=400)
            return JsonResponse(serializer.errors, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        try:
            with transaction.atomic():
                # Delete associated user account
                user = employee.user
                employee.delete()
                user.delete()
            return JsonResponse({
                'message': 'Employee deleted successfully'
            }, status=204)
        except Exception as e:
            return JsonResponse({
                'error': 'Failed to delete employee',
                'details': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@api_view(['GET'])
# @permission_classes([IsAuthenticated])  # TEMPORARILY DISABLED
def employee_by_employee_id(request, employee_id):
    """Get employee by employee_id with caching"""
    cache_key = f'employee_by_id_{employee_id}'
    employee_data = cache.get(cache_key)
    
    if employee_data is None:
        employee = get_object_or_404(
            Employee.objects.select_related('manager', 'user'), 
            employee_id=employee_id
        )
        employee_data = EmployeeSerializer(employee).data
        cache.set(cache_key, employee_data, 300)  # Cache for 5 minutes
    
    return Response({
        'employee': employee_data
    })

@api_view(['GET'])
# @permission_classes([IsAuthenticated])  # TEMPORARILY DISABLED
def employee_choices(request):
    """Get choices for dropdowns with caching"""
    choices = Employee.get_choices()
    return Response(choices)

@api_view(['GET'])
# @permission_classes([IsAuthenticated])  # TEMPORARILY DISABLED
def managers_list(request):
    """Get list of employees who can be managers with caching"""
    managers = Employee.get_active_managers()
    
    manager_list = []
    for manager in managers:
        manager_list.append({
            'id': manager['id'],
            'employee_id': manager['employee_id'],
            'full_name': f"{manager['first_name']} {manager['last_name']}"
        })
    
    return Response({
        'managers': manager_list
    })

@csrf_exempt
def debug_employee_create(request):
    """Debug endpoint to see what's happening"""
    if request.method == 'POST':
        try:
            print("Raw request body:", request.body)
            data = json.loads(request.body)
            print("Parsed data:", data)
            
            serializer = EmployeeSerializer(data=data)
            print("Serializer valid:", serializer.is_valid())
            
            if not serializer.is_valid():
                print("Serializer errors:", serializer.errors)
                return JsonResponse({
                    'validation_errors': serializer.errors,
                    'received_data': data
                }, status=400)
            
            return JsonResponse({'message': 'Validation passed'})
            
        except Exception as e:
            print("Exception:", str(e))
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)