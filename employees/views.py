from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
import json
from .models import Employee
from .serializers import EmployeeSerializer, EmployeeListSerializer

@csrf_exempt
def employee_list_create(request):
    """
    GET: List all employees
    POST: Create new employee
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method == 'GET':
        employees = Employee.objects.select_related('manager', 'user').all()
        
        # Filter by department if provided
        department = request.GET.get('department')
        if department:
            employees = employees.filter(department=department)
        
        # Filter by role if provided
        role = request.GET.get('role')
        if role:
            employees = employees.filter(role=role)
        
        # Filter by active status
        is_active = request.GET.get('is_active')
        if is_active is not None:
            employees = employees.filter(is_active=is_active.lower() == 'true')
        
        serializer = EmployeeListSerializer(employees, many=True)
        return JsonResponse({
            'count': employees.count(),
            'employees': serializer.data
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
    GET: Retrieve employee by ID
    PUT: Update employee
    DELETE: Delete employee
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        employee = Employee.objects.select_related('manager', 'user').get(pk=pk)
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
@permission_classes([IsAuthenticated])
def employee_by_employee_id(request, employee_id):
    """Get employee by employee_id"""
    employee = get_object_or_404(Employee.objects.select_related('manager', 'user'), employee_id=employee_id)
    serializer = EmployeeSerializer(employee)
    return Response({
        'employee': serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_choices(request):
    """Get choices for dropdowns"""
    return Response({
        'roles': dict(Employee.ROLE_CHOICES),
        'departments': dict(Employee.DEPARTMENT_CHOICES)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def managers_list(request):
    """Get list of employees who can be managers"""
    managers = Employee.objects.filter(
        role__in=['manager', 'admin'],
        is_active=True
    ).values('id', 'employee_id', 'first_name', 'last_name')
    
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
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)