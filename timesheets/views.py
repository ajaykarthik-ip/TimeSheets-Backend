from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from datetime import datetime, date, timedelta
import json
from .models import Timesheet
from .serializers import (
    TimesheetSerializer, TimesheetListSerializer, 
    TimesheetCreateSerializer, TimesheetSummarySerializer,
    TimesheetDraftSerializer  # NEW import
)
from employees.models import Employee
from projects.models import Project

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_employee(request):
    """Get current user's employee information for frontend"""
    try:
        employee = request.user.employee
        return Response({
            'employee_id': employee.employee_id,
            'employee_name': employee.full_name,
            'department': employee.department,
            'role': employee.role,
            'is_active': employee.is_active
        })
    except Employee.DoesNotExist:
        return Response({
            'error': 'Current user is not linked to an employee record'
        }, status=400)

@csrf_exempt
def timesheet_list_create(request):
    """
    GET: List timesheets with filtering and pagination
    POST: Create new timesheet
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method == 'GET':
        # Base queryset with optimized queries
        timesheets = Timesheet.objects.select_related(
            'employee', 'project', 'employee__user'
        ).all()
        
        # Filtering
        employee_id = request.GET.get('employee_id')
        if employee_id:
            timesheets = timesheets.filter(employee__employee_id=employee_id)
        
        project_id = request.GET.get('project_id')
        if project_id:
            timesheets = timesheets.filter(project_id=project_id)
        
        # NEW: Status filtering
        status_filter = request.GET.get('status')
        if status_filter:
            timesheets = timesheets.filter(status=status_filter)
        
        # Date filtering
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        # Default to current month if no dates provided
        if not date_from and not date_to:
            today = date.today()
            date_from = today.replace(day=1).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                timesheets = timesheets.filter(date__gte=date_from_obj)
            except ValueError:
                return JsonResponse({'error': 'Invalid date_from format. Use YYYY-MM-DD'}, status=400)
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                timesheets = timesheets.filter(date__lte=date_to_obj)
            except ValueError:
                return JsonResponse({'error': 'Invalid date_to format. Use YYYY-MM-DD'}, status=400)
        
        # Activity type filtering
        activity_type = request.GET.get('activity_type')
        if activity_type:
            timesheets = timesheets.filter(activity_type__icontains=activity_type)
        
        # If not admin, only show user's own timesheets
        if not request.user.is_staff:
            try:
                user_employee = request.user.employee
                timesheets = timesheets.filter(employee=user_employee)
            except Employee.DoesNotExist:
                return JsonResponse({'error': 'User does not have an employee record'}, status=400)
        
        # Pagination
        page_size = min(int(request.GET.get('page_size', 50)), 100)  # Max 100 per page
        page = int(request.GET.get('page', 1))
        
        paginator = Paginator(timesheets, page_size)
        page_obj = paginator.get_page(page)
        
        serializer = TimesheetListSerializer(page_obj.object_list, many=True)
        
        return JsonResponse({
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page,
            'page_size': page_size,
            'timesheets': serializer.data,
            'filters_applied': {
                'date_from': date_from,
                'date_to': date_to,
                'employee_id': employee_id,
                'project_id': project_id,
                'activity_type': activity_type,
                'status': status_filter  # NEW
            }
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            serializer = TimesheetCreateSerializer(data=data, context={'request': request})
            if serializer.is_valid():
                try:
                    with transaction.atomic():
                        timesheet = serializer.save()
                    return JsonResponse({
                        'message': 'Timesheet created successfully',
                        'timesheet': TimesheetSerializer(timesheet).data
                    }, status=201)
                except Exception as e:
                    return JsonResponse({
                        'error': 'Failed to create timesheet',
                        'details': str(e)
                    }, status=400)
            return JsonResponse(serializer.errors, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def timesheet_detail(request, pk):
    """
    GET: Retrieve timesheet by ID
    PUT: Update timesheet
    DELETE: Delete timesheet
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        timesheet = Timesheet.objects.select_related(
            'employee', 'project', 'employee__user'
        ).get(pk=pk)
    except Timesheet.DoesNotExist:
        return JsonResponse({'error': 'Timesheet not found'}, status=404)
    
    # Check if user can access this timesheet
    if not request.user.is_staff and timesheet.employee.user != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if request.method == 'GET':
        serializer = TimesheetSerializer(timesheet)
        return JsonResponse({
            'timesheet': serializer.data
        })
    
    elif request.method == 'PUT':
        # NEW: Check if timesheet can be edited
        if not timesheet.can_edit:
            return JsonResponse({'error': 'Cannot edit submitted timesheet'}, status=400)
        
        try:
            data = json.loads(request.body)
            serializer = TimesheetSerializer(timesheet, data=data, partial=True)
            if serializer.is_valid():
                try:
                    with transaction.atomic():
                        timesheet = serializer.save()
                    return JsonResponse({
                        'message': 'Timesheet updated successfully',
                        'timesheet': TimesheetSerializer(timesheet).data
                    })
                except Exception as e:
                    return JsonResponse({
                        'error': 'Failed to update timesheet',
                        'details': str(e)
                    }, status=400)
            return JsonResponse(serializer.errors, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        # NEW: Check if timesheet can be deleted (only drafts)
        if timesheet.status == 'submitted':
            return JsonResponse({'error': 'Cannot delete submitted timesheet'}, status=400)
        
        try:
            with transaction.atomic():
                timesheet.delete()
            return JsonResponse({
                'message': 'Timesheet deleted successfully'
            }, status=204)
        except Exception as e:
            return JsonResponse({
                'error': 'Failed to delete timesheet',
                'details': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_timesheets(request):
    """Get current user's timesheets"""
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return Response({'error': 'User does not have an employee record'}, status=400)
    
    # Date filtering with defaults
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        # Default to current week
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        date_from = start_of_week.strftime('%Y-%m-%d')
    
    if not date_to:
        date_to = date.today().strftime('%Y-%m-%d')
    
    timesheets = Timesheet.objects.filter(
        employee=employee,
        date__gte=date_from,
        date__lte=date_to
    ).select_related('project').order_by('-date')
    
    serializer = TimesheetListSerializer(timesheets, many=True)
    
    # Calculate summary
    total_hours = timesheets.aggregate(total=Sum('hours_worked'))['total'] or 0
    draft_count = timesheets.filter(status='draft').count()
    submitted_count = timesheets.filter(status='submitted').count()
    
    return Response({
        'timesheets': serializer.data,
        'summary': {
            'total_hours': float(total_hours),
            'total_entries': timesheets.count(),
            'draft_count': draft_count,      # NEW
            'submitted_count': submitted_count,  # NEW
            'date_range': f"{date_from} to {date_to}"
        }
    })

# NEW FUNCTION: Get user's drafts
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def drafts_list(request):
    """Get current user's draft timesheets"""
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return Response({'error': 'User does not have an employee record'}, status=400)
    
    drafts = Timesheet.objects.filter(
        employee=employee,
        status='draft'
    ).select_related('project').order_by('-created_at')
    
    serializer = TimesheetDraftSerializer(drafts, many=True)
    
    return Response({
        'drafts': serializer.data,
        'total_drafts': drafts.count()
    })

# NEW FUNCTION: Submit a draft
@csrf_exempt
def submit_timesheet(request, pk):
    """Submit a draft timesheet"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method != 'PUT':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        timesheet = Timesheet.objects.get(pk=pk)
    except Timesheet.DoesNotExist:
        return JsonResponse({'error': 'Timesheet not found'}, status=404)
    
    # Check permissions
    if not request.user.is_staff and timesheet.employee.user != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Check if it's a draft
    if timesheet.status != 'draft':
        return JsonResponse({'error': 'Only draft timesheets can be submitted'}, status=400)
    
    try:
        with transaction.atomic():
            timesheet.submit()
        
        return JsonResponse({
            'message': 'Timesheet submitted successfully',
            'timesheet': TimesheetSerializer(timesheet).data
        })
    except Exception as e:
        return JsonResponse({
            'error': 'Failed to submit timesheet',
            'details': str(e)
        }, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def timesheet_summary(request):
    """Get timesheet summary/analytics"""
    if not request.user.is_staff:
        try:
            employee = request.user.employee
            base_filter = {'employee': employee}
        except Employee.DoesNotExist:
            return Response({'error': 'User does not have an employee record'}, status=400)
    else:
        base_filter = {}
    
    # Date filtering
    date_from = request.GET.get('date_from', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', date.today().strftime('%Y-%m-%d'))
    
    # Daily summary
    daily_summary = Timesheet.objects.filter(
        date__gte=date_from,
        date__lte=date_to,
        **base_filter
    ).values('date').annotate(
        total_hours=Sum('hours_worked'),
        project_count=Count('project', distinct=True)
    ).order_by('date')
    
    # Project summary
    project_summary = Timesheet.objects.filter(
        date__gte=date_from,
        date__lte=date_to,
        **base_filter
    ).values('project__name').annotate(
        total_hours=Sum('hours_worked'),
        entry_count=Count('id')
    ).order_by('-total_hours')
    
    # Activity summary
    activity_summary = Timesheet.objects.filter(
        date__gte=date_from,
        date__lte=date_to,
        **base_filter
    ).values('activity_type').annotate(
        total_hours=Sum('hours_worked'),
        entry_count=Count('id')
    ).order_by('-total_hours')
    
    return Response({
        'daily_summary': list(daily_summary),
        'project_summary': list(project_summary),
        'activity_summary': list(activity_summary),
        'date_range': f"{date_from} to {date_to}"
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_activities(request, project_id):
    """Get available activity types for a specific project"""
    try:
        project = Project.objects.get(id=project_id)
        return Response({
            'project_id': project_id,
            'project_name': project.name,
            'activity_types': project.get_activity_types()
        })
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)

@csrf_exempt
def debug_timesheet_create(request):
    """Debug endpoint for timesheet creation"""
    if request.method == 'POST':
        try:
            print("Raw request body:", request.body)
            data = json.loads(request.body)
            print("Parsed data:", data)
            
            serializer = TimesheetCreateSerializer(data=data, context={'request': request})
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