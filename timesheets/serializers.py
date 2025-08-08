from rest_framework import serializers
from django.db.models import Sum
from datetime import date
from django.utils import timezone
from .models import Timesheet
from employees.models import Employee
from projects.models import Project

class TimesheetSerializer(serializers.ModelSerializer):
    """Full serializer for detail views and create/update operations - MODIFIED"""
    # Read-only fields for display
    employee_name = serializers.ReadOnlyField()
    project_name = serializers.ReadOnlyField()
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    can_edit = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # For easier frontend handling
    project_activity_types = serializers.SerializerMethodField(read_only=True)
    daily_total_hours = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Timesheet
        fields = [
            'id', 'employee', 'employee_id', 'employee_name', 'project', 'project_name',
            'activity_type', 'date', 'hours_worked', 'description', 'status', 'status_display',
            'can_edit', 'project_activity_types', 'daily_total_hours',
            'created_at', 'updated_at', 'submitted_at'
        ]
        read_only_fields = [
            'id', 'employee_name', 'project_name', 'can_edit', 'status_display', 
            'created_at', 'updated_at', 'submitted_at', 'status'  # ADDED status as read-only
        ]
    
    def get_project_activity_types(self, obj):
        """Return available activity types for the project"""
        return obj.project.get_activity_types() if obj.project else []
    
    def get_daily_total_hours(self, obj):
        """Return total hours worked by employee on this date"""
        return float(obj.total_hours_for_date)
    
    def validate(self, data):
        """Cross-field validation - prevent individual submission"""
        # If someone tries to change status to submitted, block it
        if 'status' in data and data['status'] == 'submitted':
            raise serializers.ValidationError({
                'status': 'Individual submission not allowed. Use weekly bulk submission.'
            })
        
        # Force status to remain draft for updates
        data['status'] = 'draft'
        
        return data
class TimesheetListSerializer(serializers.ModelSerializer):
    """Optimized serializer for list views - minimal fields"""
    employee_name = serializers.ReadOnlyField()
    project_name = serializers.ReadOnlyField()
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    can_edit = serializers.ReadOnlyField()
    
    class Meta:
        model = Timesheet
        fields = [
            'id', 'employee_id', 'employee_name', 'project_name',
            'activity_type', 'date', 'hours_worked', 'description',
            'status', 'status_display', 'can_edit', 'created_at', 'submitted_at'
        ]

class TimesheetSummarySerializer(serializers.Serializer):
    """Serializer for summary/aggregated data"""
    date = serializers.DateField()
    total_hours = serializers.DecimalField(max_digits=6, decimal_places=2)
    project_name = serializers.CharField()
    project_count = serializers.IntegerField()

class TimesheetCreateSerializer(serializers.ModelSerializer):
    """Serializer for timesheet creation - ALWAYS creates drafts only"""
    employee_id = serializers.CharField(write_only=True, help_text="Employee ID (required)")
    
    class Meta:
        model = Timesheet
        fields = [
            'employee_id', 'project', 'activity_type', 'date', 'hours_worked', 'description'
            # REMOVED 'status' from fields - will always be 'draft'
        ]
    
    def validate_employee_id(self, value):
        """Validate employee exists"""
        try:
            employee = Employee.objects.get(employee_id=value)
            return value
        except Employee.DoesNotExist:
            raise serializers.ValidationError(f"Employee with ID '{value}' not found.")
    
    def validate(self, data):
        """Cross-field validation and permission checks"""
        request = self.context.get('request')
        employee_id = data.pop('employee_id')
        
        # Get employee object by employee_id
        try:
            employee = Employee.objects.get(employee_id=employee_id)
            data['employee'] = employee
        except Employee.DoesNotExist:
            raise serializers.ValidationError(f"Employee with ID '{employee_id}' not found.")
        
        # Permission check: Users can only create timesheets for themselves (unless admin)
        if request and request.user.is_authenticated:
            if not request.user.is_staff:
                try:
                    user_employee = request.user.employee
                    if user_employee != employee:
                        raise serializers.ValidationError("You can only create timesheets for yourself.")
                except Employee.DoesNotExist:
                    raise serializers.ValidationError("Your user account is not linked to an employee record.")
        
        # FORCE status to be draft
        data['status'] = 'draft'
        
        # Relaxed validation for drafts - only basic checks
        project = data.get('project')
        if project and project.status != 'active':
            raise serializers.ValidationError("Cannot create timesheet for inactive project.")
        
        if not employee.is_active:
            raise serializers.ValidationError("Cannot create timesheet for inactive employee.")
        
        return data
    
class TimesheetDraftSerializer(serializers.ModelSerializer):
    """Serializer specifically for draft operations"""
    employee_name = serializers.ReadOnlyField()
    project_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Timesheet
        fields = [
            'id', 'employee_name', 'project_name', 'activity_type', 
            'date', 'hours_worked', 'description', 'created_at'
        ]

class WeekSubmissionSerializer(serializers.Serializer):
    """Serializer for submitting a week's worth of timesheets"""
    week_start_date = serializers.DateField(
        help_text="Monday of the week to submit (YYYY-MM-DD format)"
    )
    timesheet_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Optional: Specific timesheet IDs to submit. If not provided, all drafts for the week will be submitted."
    )
    force_submit = serializers.BooleanField(
        default=False,
        help_text="Submit even if there are warnings (but not errors)"
    )
    
    def validate_week_start_date(self, value):
        """Ensure the date is a Monday"""
        if value.weekday() != 0:  # 0 = Monday
            raise serializers.ValidationError("Week start date must be a Monday")
        return value
    
    def validate_timesheet_ids(self, value):
        """Validate that all timesheet IDs exist and are drafts"""
        if value:
            from .models import Timesheet
            
            # Check if all IDs exist
            existing_ids = set(Timesheet.objects.filter(id__in=value).values_list('id', flat=True))
            provided_ids = set(value)
            missing_ids = provided_ids - existing_ids
            
            if missing_ids:
                raise serializers.ValidationError(f"Timesheet IDs not found: {list(missing_ids)}")
            
            # Check if all are drafts
            non_draft_ids = list(Timesheet.objects.filter(
                id__in=value, 
                status__ne='draft'
            ).values_list('id', flat=True))
            
            if non_draft_ids:
                raise serializers.ValidationError(f"These timesheets are not drafts: {non_draft_ids}")
        
        return value

class WeekSummarySerializer(serializers.Serializer):
    """Serializer for week summary data"""
    week_start_date = serializers.DateField()
    week_end_date = serializers.DateField()
    week_range = serializers.CharField()
    total_hours = serializers.DecimalField(max_digits=6, decimal_places=2)
    total_entries = serializers.IntegerField()
    unique_projects = serializers.IntegerField()
    unique_dates = serializers.IntegerField()
    draft_count = serializers.IntegerField()
    submitted_count = serializers.IntegerField()
    daily_totals = serializers.DictField()
    project_totals = serializers.DictField()
    timesheets = TimesheetListSerializer(many=True)

class WeekValidationSerializer(serializers.Serializer):
    """Serializer for week validation results"""
    is_valid = serializers.BooleanField()
    has_warnings = serializers.BooleanField()
    timesheet_errors = serializers.ListField()
    week_warnings = serializers.ListField()
    summary = serializers.DictField()

class BulkTimesheetActionSerializer(serializers.Serializer):
    """Serializer for bulk actions on multiple timesheets"""
    timesheet_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of timesheet IDs to perform action on"
    )
    action = serializers.ChoiceField(
        choices=['submit', 'delete', 'validate'],
        help_text="Action to perform on selected timesheets"
    )
    
    def validate_timesheet_ids(self, value):
        """Validate timesheet IDs exist"""
        if not value:
            raise serializers.ValidationError("At least one timesheet ID is required")
        
        from .models import Timesheet
        existing_count = Timesheet.objects.filter(id__in=value).count()
        
        if existing_count != len(value):
            raise serializers.ValidationError("One or more timesheet IDs not found")
        
        return value

class WeeklyTimesheetCreateSerializer(serializers.Serializer):
    """Serializer for creating multiple timesheets for a week"""
    week_start_date = serializers.DateField()
    timesheets = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of timesheet data for the week"
    )
    
    def validate_timesheets(self, value):
        """Validate each timesheet in the list"""
        if not value:
            raise serializers.ValidationError("At least one timesheet is required")
        
        errors = []
        for i, timesheet_data in enumerate(value):
            try:
                # Validate each timesheet using existing serializer
                serializer = TimesheetCreateSerializer(data=timesheet_data)
                if not serializer.is_valid():
                    errors.append(f"Timesheet {i+1}: {serializer.errors}")
            except Exception as e:
                errors.append(f"Timesheet {i+1}: {str(e)}")
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return value