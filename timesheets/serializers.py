from rest_framework import serializers
from django.db.models import Sum
from datetime import date
from .models import Timesheet
from employees.models import Employee
from projects.models import Project

class TimesheetSerializer(serializers.ModelSerializer):
    # Read-only fields for display
    employee_name = serializers.ReadOnlyField()
    project_name = serializers.ReadOnlyField()
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    
    # For easier frontend handling
    project_activity_types = serializers.SerializerMethodField(read_only=True)
    daily_total_hours = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Timesheet
        fields = [
            'id', 'employee', 'employee_id', 'employee_name', 'project', 'project_name',
            'activity_type', 'date', 'hours_worked', 'description',
            'project_activity_types', 'daily_total_hours',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'employee_name', 'project_name', 'created_at', 'updated_at']
    
    def get_project_activity_types(self, obj):
        """Return available activity types for the project"""
        return obj.project.get_activity_types() if obj.project else []
    
    def get_daily_total_hours(self, obj):
        """Return total hours worked by employee on this date"""
        return float(obj.total_hours_for_date)
    
    def validate_date(self, value):
        """Validate date is not in the future"""
        if value > date.today():
            raise serializers.ValidationError("Date cannot be in the future.")
        return value
    
    def validate_hours_worked(self, value):
        """Validate hours worked is reasonable"""
        if value <= 0:
            raise serializers.ValidationError("Hours worked must be greater than 0.")
        if value > 24:
            raise serializers.ValidationError("Hours worked cannot exceed 24 hours per day.")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
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
        
        # Check for duplicate entry (during creation)
        if not self.instance:  # Only check during creation
            existing = Timesheet.objects.filter(
                employee=employee,
                project=project,
                date=date_val,
                activity_type=activity_type
            ).exists()
            
            if existing:
                raise serializers.ValidationError(
                    "A timesheet entry already exists for this employee, project, date, and activity type."
                )
        
        # Check daily hours limit (optional - can be configured)
        if employee and date_val and hours_worked:
            current_daily_total = Timesheet.objects.filter(
                employee=employee,
                date=date_val
            ).exclude(id=self.instance.id if self.instance else None).aggregate(
                total=Sum('hours_worked')
            )['total'] or 0
            
            if current_daily_total + hours_worked > 24:
                raise serializers.ValidationError({
                    'hours_worked': f'Total daily hours would exceed 24. Current total: {current_daily_total}'
                })
        
        return data

class TimesheetListSerializer(serializers.ModelSerializer):
    """Optimized serializer for list views - minimal fields"""
    employee_name = serializers.ReadOnlyField()
    project_name = serializers.ReadOnlyField()
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    
    class Meta:
        model = Timesheet
        fields = [
            'id', 'employee_id', 'employee_name', 'project_name',
            'activity_type', 'date', 'hours_worked', 'description'
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
            'employee_id', 'project', 'activity_type', 'date', 'hours_worked', 'description'
        ]
    
    def validate_project(self, value):
        """Ensure project is active"""
        if value.status != 'active':
            raise serializers.ValidationError("Cannot create timesheet for inactive project.")
        return value
    
    def validate_employee_id(self, value):
        """Validate employee exists and is active"""
        try:
            employee = Employee.objects.get(employee_id=value)
            if not employee.is_active:
                raise serializers.ValidationError("Cannot create timesheet for inactive employee.")
            return value
        except Employee.DoesNotExist:
            raise serializers.ValidationError(f"Employee with ID '{value}' not found.")
    
    def validate(self, data):
        """Cross-field validation and permission checks"""
        request = self.context.get('request')
        employee_id = data.pop('employee_id')  # Remove from data since it's not a model field
        
        # Get employee object by employee_id (not by primary key)
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
        
        # Validate activity type against project
        project = data.get('project')
        activity_type = data.get('activity_type')
        
        if project and activity_type:
            valid_activities = project.get_activity_types()
            if valid_activities and activity_type not in valid_activities:
                raise serializers.ValidationError({
                    'activity_type': f'Activity type must be one of: {", ".join(valid_activities)}'
                })
        
        # Check for duplicate entry
        date_val = data.get('date')
        if employee and project and date_val and activity_type:
            existing = Timesheet.objects.filter(
                employee=employee,
                project=project,
                date=date_val,
                activity_type=activity_type
            ).exists()
            
            if existing:
                raise serializers.ValidationError(
                    f"A timesheet entry already exists for employee {employee_id}, project {project.name}, date {date_val}, and activity {activity_type}."
                )
        
        return data