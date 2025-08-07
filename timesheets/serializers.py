from rest_framework import serializers
from django.db.models import Sum
from datetime import date
from django.utils import timezone
from .models import Timesheet
from employees.models import Employee
from projects.models import Project

class TimesheetSerializer(serializers.ModelSerializer):
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
        read_only_fields = ['id', 'employee_name', 'project_name', 'can_edit', 'status_display', 
                           'created_at', 'updated_at', 'submitted_at']
    
    def get_project_activity_types(self, obj):
        """Return available activity types for the project"""
        return obj.project.get_activity_types() if obj.project else []
    
    def get_daily_total_hours(self, obj):
        """Return total hours worked by employee on this date"""
        return float(obj.total_hours_for_date)
    
    def validate_date(self, value):
        """Validate date - relaxed for drafts"""
        if self.initial_data.get('status') == 'submitted' and value > date.today():
            raise serializers.ValidationError("Date cannot be in the future for submitted timesheets.")
        return value
    
    def validate_hours_worked(self, value):
        """Validate hours worked - relaxed for drafts"""
        if value <= 0:
            raise serializers.ValidationError("Hours worked must be greater than 0.")
        if self.initial_data.get('status') == 'submitted' and value > 24:
            raise serializers.ValidationError("Hours worked cannot exceed 24 hours per day.")
        return value
    
    def validate(self, data):
        """Cross-field validation - only strict for submitted"""
        status = data.get('status', 'draft')
        
        if status == 'submitted':
            project = data.get('project')
            activity_type = data.get('activity_type')
            employee = data.get('employee')
            date_val = data.get('date')
            hours_worked = data.get('hours_worked', 0)
            
            # Validate activity type against project
            if project and activity_type:
                valid_activities = project.get_activity_types()
                if valid_activities and activity_type not in valid_activities:
                    raise serializers.ValidationError({
                        'activity_type': f'Activity type must be one of: {", ".join(valid_activities)}'
                    })
            
            # Check for duplicate submitted entry (during creation)
            if not self.instance:  # Only check during creation
                existing = Timesheet.objects.filter(
                    employee=employee,
                    project=project,
                    date=date_val,
                    activity_type=activity_type,
                    status='submitted'
                ).exists()
                
                if existing:
                    raise serializers.ValidationError(
                        "A submitted timesheet entry already exists for this employee, project, date, and activity type."
                    )
        
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
    """Serializer for timesheet creation with explicit employee_id"""
    employee_id = serializers.CharField(write_only=True, help_text="Employee ID (required)")
    
    class Meta:
        model = Timesheet
        fields = [
            'employee_id', 'project', 'activity_type', 'date', 'hours_worked', 'description', 'status'
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
        employee_id = data.pop('employee_id')  # Remove from data since it's not a model field
        status = data.get('status', 'draft')
        
        # Get employee object by employee_id
        try:
            employee = Employee.objects.get(employee_id=employee_id)
            data['employee'] = employee  # Add the actual Employee object
        except Employee.DoesNotExist:
            raise serializers.ValidationError(f"Employee with ID '{employee_id}' not found.")
        
        # Permission check: Users can only create timesheets for themselves (unless admin)
        if request and request.user.is_authenticated:
            if not request.user.is_staff:  # Regular users
                try:
                    user_employee = request.user.employee
                    if user_employee != employee:
                        raise serializers.ValidationError("You can only create timesheets for yourself.")
                except Employee.DoesNotExist:
                    raise serializers.ValidationError("Your user account is not linked to an employee record.")
        
        # Only validate business rules for submitted timesheets
        if status == 'submitted':
            project = data.get('project')
            activity_type = data.get('activity_type')
            date_val = data.get('date')
            
            # Validate activity type against project
            if project and activity_type:
                valid_activities = project.get_activity_types()
                if valid_activities and activity_type not in valid_activities:
                    raise serializers.ValidationError({
                        'activity_type': f'Activity type must be one of: {", ".join(valid_activities)}'
                    })
            
            # Check for duplicate submitted entry
            if employee and project and date_val and activity_type:
                existing = Timesheet.objects.filter(
                    employee=employee,
                    project=project,
                    date=date_val,
                    activity_type=activity_type,
                    status='submitted'
                ).exists()
                
                if existing:
                    raise serializers.ValidationError(
                        f"A submitted timesheet already exists for employee {employee_id}, project {project.name}, date {date_val}, and activity {activity_type}."
                    )
        
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
