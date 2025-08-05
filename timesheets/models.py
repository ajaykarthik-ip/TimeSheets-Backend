from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from employees.models import Employee
from projects.models import Project
from datetime import date
import json

class Timesheet(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='timesheets')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='timesheets')
    activity_type = models.CharField(max_length=100)
    date = models.DateField()
    hours_worked = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0.1), MaxValueValidator(24.0)]
    )
    description = models.TextField(blank=True, null=True)
    
    # Denormalized fields for faster queries
    employee_name = models.CharField(max_length=101, blank=True)  # first_name + last_name
    project_name = models.CharField(max_length=200, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        # Unique constraint to prevent duplicate entries
        unique_together = ['employee', 'project', 'date', 'activity_type']
        
        # Database indexes for performance
        indexes = [
            models.Index(fields=['employee', 'date']),  # Most common query
            models.Index(fields=['project', 'date']),   # Project reporting
            models.Index(fields=['date']),              # Date range queries
            models.Index(fields=['employee', 'project', 'date']),  # Combined queries
            models.Index(fields=['-created_at']),       # Recent entries
        ]
    
    def __str__(self):
        return f"{self.employee_name} - {self.project_name} - {self.date}"
    
    def clean(self):
        """Model-level validation"""
        # Check if date is not in the future
        if self.date and self.date > date.today():
            raise ValidationError('Date cannot be in the future.')
        
        # Validate activity type exists in project
        if self.project and self.activity_type:
            project_activities = self.project.get_activity_types()
            if project_activities and self.activity_type not in project_activities:
                raise ValidationError(
                    f'Activity type "{self.activity_type}" is not valid for project "{self.project.name}". '
                    f'Valid activities: {", ".join(project_activities)}'
                )
        
        # Check if employee is active
        if self.employee and not self.employee.is_active:
            raise ValidationError('Cannot create timesheet for inactive employee.')
        
        # Check if project is active
        if self.project and self.project.status != 'active':
            raise ValidationError('Cannot create timesheet for inactive project.')
    
    def save(self, *args, **kwargs):
        # Auto-populate denormalized fields
        if self.employee:
            self.employee_name = self.employee.full_name
        if self.project:
            self.project_name = self.project.name
        
        # Run validations
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def total_hours_for_date(self):
        """Get total hours worked by this employee on this date"""
        return Timesheet.objects.filter(
            employee=self.employee,
            date=self.date
        ).aggregate(total=models.Sum('hours_worked'))['total'] or 0