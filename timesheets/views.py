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

from .utils import (
    get_week_start_end_dates, get_week_drafts, 
    calculate_week_totals, validate_week_timesheets, format_week_range
)
from .serializers import (
    WeekSubmissionSerializer, WeekSummarySerializer, 
    WeekValidationSerializer, BulkTimesheetActionSerializer
)

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
    POST: Create new timesheet (ALWAYS as draft)
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method == 'GET':
        # Optimized base queryset with select_related and prefetch_related
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
        
        # Status filtering
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
                'status': status_filter
            }
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # FORCE status to be 'draft' - ignore any submitted status
            data['status'] = 'draft'
            
            serializer = TimesheetCreateSerializer(data=data, context={'request': request})
            if serializer.is_valid():
                try:
                    with transaction.atomic():
                        timesheet = serializer.save()
                    return JsonResponse({
                        'message': 'Timesheet draft created successfully',
                        'note': 'Use weekly submission to submit all drafts at once',
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
    PUT: Update timesheet (but prevent individual submission)
    DELETE: Delete timesheet (only drafts)
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
        # Only allow editing of drafts
        if timesheet.status != 'draft':
            return JsonResponse({
                'error': 'Cannot edit submitted timesheet',
                'message': 'Only draft timesheets can be modified'
            }, status=400)
        
        try:
            data = json.loads(request.body)
            
            # PREVENT individual submission through update
            if data.get('status') == 'submitted':
                return JsonResponse({
                    'error': 'Individual submission not allowed',
                    'message': 'Use weekly bulk submission instead: POST /api/timesheets/submit-week/'
                }, status=400)
            
            # Force status to remain draft
            data['status'] = 'draft'
            
            serializer = TimesheetSerializer(timesheet, data=data, partial=True)
            if serializer.is_valid():
                try:
                    with transaction.atomic():
                        timesheet = serializer.save()
                    return JsonResponse({
                        'message': 'Timesheet draft updated successfully',
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
        # Only allow deletion of drafts
        if timesheet.status == 'submitted':
            return JsonResponse({
                'error': 'Cannot delete submitted timesheet'
            }, status=400)
        
        try:
            with transaction.atomic():
                timesheet.delete()
            return JsonResponse({
                'message': 'Timesheet draft deleted successfully'
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
            'draft_count': draft_count,
            'submitted_count': submitted_count,
            'date_range': f"{date_from} to {date_to}"
        }
    })

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

@csrf_exempt
def submit_timesheet(request, pk):
    """
    DISABLED: Individual timesheet submission not allowed
    Use weekly bulk submission instead
    """
    return JsonResponse({
        'error': 'Individual timesheet submission is disabled',
        'message': 'Please use weekly bulk submission: POST /api/timesheets/submit-week/',
        'help': 'Create drafts during the week and submit all at once'
    }, status=405)

@csrf_exempt
def submit_week_timesheets(request):
    """
    Submit all draft timesheets for a specific week
    POST /api/timesheets/submit-week/
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get user's employee record
        try:
            employee = request.user.employee
        except Employee.DoesNotExist:
            return JsonResponse({'error': 'User does not have an employee record'}, status=400)
        
        # Parse and validate request data
        data = json.loads(request.body)
        serializer = WeekSubmissionSerializer(data=data)
        
        if not serializer.is_valid():
            return JsonResponse({
                'error': 'Invalid request data',
                'details': serializer.errors
            }, status=400)
        
        week_start_date = serializer.validated_data['week_start_date']
        specific_ids = serializer.validated_data.get('timesheet_ids')
        force_submit = serializer.validated_data.get('force_submit', False)
        
        # Get timesheets to submit
        if specific_ids:
            # Submit specific timesheets (must be user's own and drafts)
            week_start, week_end = get_week_start_end_dates(week_start_date)
            timesheets_to_submit = Timesheet.objects.filter(
                id__in=specific_ids,
                employee=employee,
                status='draft',
                date__gte=week_start,
                date__lte=week_end
            ).select_related('project', 'employee')
        else:
            # Submit all drafts for the week
            timesheets_to_submit = get_week_drafts(employee, week_start_date)
        
        if not timesheets_to_submit.exists():
            return JsonResponse({
                'error': 'No draft timesheets found for the specified week',
                'week_range': format_week_range(week_start_date)
            }, status=404)
        
        # Convert QuerySet to list and ensure related objects are loaded
        timesheet_list = list(timesheets_to_submit.select_related('project', 'employee'))
        
        print(f"DEBUG: About to validate {len(timesheet_list)} timesheets")
        
        # Validate all timesheets before submission
        try:
            validation_result = validate_week_timesheets(timesheet_list)
            print("DEBUG: Validation completed successfully")
        except Exception as validation_error:
            print(f"DEBUG: Validation failed with error: {validation_error}")
            return JsonResponse({
                'error': 'Validation failed',
                'details': str(validation_error),
                'week_range': format_week_range(week_start_date),
                'debug_info': f'Error with {len(timesheet_list) if timesheet_list else 0} timesheets'
            }, status=400)
        
        # Check if submission should be blocked
        if not validation_result['is_valid']:
            return JsonResponse({
                'error': 'Week submission failed validation',
                'validation_errors': validation_result['timesheet_errors'],
                'week_warnings': validation_result['week_warnings'],
                'message': 'Please fix the errors and try again'
            }, status=400)
        
        # Check warnings (can be overridden with force_submit)
        if validation_result['has_warnings'] and not force_submit:
            return JsonResponse({
                'error': 'Week has warnings',
                'validation_warnings': validation_result['timesheet_errors'],
                'week_warnings': validation_result['week_warnings'],
                'message': 'Review warnings and use force_submit=true to proceed',
                'can_force_submit': True
            }, status=400)
        
        # Perform the bulk submission
        submitted_timesheets = []
        failed_submissions = []
        
        print("DEBUG: About to start submission loop")
        
        try:
            with transaction.atomic():
                for i, timesheet in enumerate(timesheet_list):
                    print(f"DEBUG: Submitting timesheet {i+1}/{len(timesheet_list)} - ID: {timesheet.id}")
                    try:
                        timesheet.submit()  # This will set status and submitted_at
                        submitted_timesheets.append(timesheet)
                        print(f"DEBUG: Successfully submitted timesheet {timesheet.id}")
                    except Exception as e:
                        print(f"DEBUG: Failed to submit timesheet {timesheet.id}: {str(e)}")
                        failed_submissions.append({
                            'timesheet_id': timesheet.id,
                            'error': str(e)
                        })
                
                # If any submissions failed, rollback the transaction
                if failed_submissions:
                    raise Exception("Some timesheets failed to submit")
        
        except Exception as e:
            return JsonResponse({
                'error': 'Week submission failed',
                'failed_submissions': failed_submissions,
                'details': str(e)
            }, status=400)
        
        # Calculate summary for response
        summary = calculate_week_totals(submitted_timesheets)
        
        return JsonResponse({
            'message': 'Week submitted successfully',
            'week_range': format_week_range(week_start_date),
            'submitted_count': len(submitted_timesheets),
            'total_hours': summary['total_hours'],
            'summary': summary,
            'submitted_timesheets': TimesheetListSerializer(submitted_timesheets, many=True).data
        }, status=200)
        
    except Exception as e:
        return JsonResponse({
            'error': 'Week submission failed',
            'details': str(e)
        }, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_week_summary(request):
    """
    Get summary of timesheets for a specific week
    GET /api/timesheets/week-summary/?week_start=2025-08-04
    """
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return Response({'error': 'User does not have an employee record'}, status=400)
    
    # Get week_start parameter
    week_start_param = request.GET.get('week_start')
    if not week_start_param:
        # Default to current week
        today = date.today()
        week_start_date = today - timedelta(days=today.weekday())
    else:
        try:
            week_start_date = datetime.strptime(week_start_param, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid week_start format. Use YYYY-MM-DD'}, status=400)
    
    # Get week boundaries
    week_start, week_end = get_week_start_end_dates(week_start_date)
    
    # Get all timesheets for the week (both draft and submitted)
    week_timesheets = Timesheet.objects.filter(
        employee=employee,
        date__gte=week_start,
        date__lte=week_end
    ).select_related('project').order_by('date', 'created_at')
    
    # Separate drafts and submitted
    draft_timesheets = week_timesheets.filter(status='draft')
    submitted_timesheets = week_timesheets.filter(status='submitted')
    
    # Calculate totals
    week_totals = calculate_week_totals(week_timesheets)
    
    # Prepare response data
    response_data = {
        'week_start_date': week_start,
        'week_end_date': week_end,
        'week_range': format_week_range(week_start_date),
        'total_hours': week_totals['total_hours'],
        'total_entries': week_totals['total_entries'],
        'unique_projects': week_totals['unique_projects'],
        'unique_dates': week_totals['unique_dates'],
        'draft_count': draft_timesheets.count(),
        'submitted_count': submitted_timesheets.count(),
        'daily_totals': week_totals['daily_totals'],
        'project_totals': week_totals['project_totals'],
        'timesheets': TimesheetListSerializer(week_timesheets, many=True).data
    }
    
    return Response(response_data)

@csrf_exempt
def validate_week_timesheets_view(request):
    """
    Validate draft timesheets for a specific week without submitting
    POST /api/timesheets/validate-week/
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return JsonResponse({'error': 'User does not have an employee record'}, status=400)
    
    try:
        data = json.loads(request.body)
        week_start_date = data.get('week_start_date')
        
        if not week_start_date:
            return JsonResponse({'error': 'week_start_date is required'}, status=400)
        
        try:
            week_start_date = datetime.strptime(week_start_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        
        # Get draft timesheets for the week
        draft_timesheets = get_week_drafts(employee, week_start_date)
        
        if not draft_timesheets.exists():
            return JsonResponse({
                'message': 'No draft timesheets found for validation',
                'week_range': format_week_range(week_start_date),
                'is_valid': True,
                'has_warnings': False
            })
        
        # Validate the timesheets
        validation_result = validate_week_timesheets(list(draft_timesheets))
        
        return JsonResponse({
            'week_range': format_week_range(week_start_date),
            'validation_result': validation_result,
            'timesheets_checked': draft_timesheets.count()
        })
        
    except Exception as e:
        return JsonResponse({
            'error': 'Validation failed',
            'details': str(e)
        }, status=400)

@csrf_exempt 
def bulk_timesheet_actions(request):
    """
    Perform bulk actions on multiple timesheets
    POST /api/timesheets/bulk-actions/
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return JsonResponse({'error': 'User does not have an employee record'}, status=400)
    
    try:
        data = json.loads(request.body)
        serializer = BulkTimesheetActionSerializer(data=data)
        
        if not serializer.is_valid():
            return JsonResponse(serializer.errors, status=400)
        
        timesheet_ids = serializer.validated_data['timesheet_ids']
        action = serializer.validated_data['action']
        
        # Get timesheets (ensure they belong to the user)
        timesheets = Timesheet.objects.filter(
            id__in=timesheet_ids,
            employee=employee
        )
        
        if timesheets.count() != len(timesheet_ids):
            return JsonResponse({
                'error': 'Some timesheets not found or do not belong to you'
            }, status=404)
        
        # Perform the requested action
        if action == 'submit':
            # Submit selected timesheets
            draft_timesheets = timesheets.filter(status='draft')
            
            if not draft_timesheets.exists():
                return JsonResponse({'error': 'No draft timesheets to submit'}, status=400)
            
            # Validate before submitting
            validation_result = validate_week_timesheets(list(draft_timesheets))
            if not validation_result['is_valid']:
                return JsonResponse({
                    'error': 'Validation failed',
                    'validation_errors': validation_result
                }, status=400)
            
            # Submit all
            submitted_count = 0
            with transaction.atomic():
                for timesheet in draft_timesheets:
                    timesheet.submit()
                    submitted_count += 1
            
            return JsonResponse({
                'message': f'Successfully submitted {submitted_count} timesheets',
                'submitted_count': submitted_count
            })
        
        elif action == 'delete':
            # Delete selected timesheets (only drafts)
            draft_timesheets = timesheets.filter(status='draft')
            
            if not draft_timesheets.exists():
                return JsonResponse({'error': 'No draft timesheets to delete'}, status=400)
            
            deleted_count = draft_timesheets.count()
            draft_timesheets.delete()
            
            return JsonResponse({
                'message': f'Successfully deleted {deleted_count} draft timesheets',
                'deleted_count': deleted_count
            })
        
        elif action == 'validate':
            # Validate selected timesheets
            validation_result = validate_week_timesheets(list(timesheets))
            
            return JsonResponse({
                'message': 'Validation completed',
                'validation_result': validation_result
            })
        
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
            
    except Exception as e:
        return JsonResponse({
            'error': 'Bulk action failed',
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