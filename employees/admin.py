from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'full_name', 'email', 'role', 'department', 'manager', 'is_active', 'hire_date']
    list_filter = ['role', 'department', 'is_active', 'hire_date']
    search_fields = ['employee_id', 'first_name', 'last_name', 'email']
    ordering = ['employee_id']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('employee_id', 'user', 'first_name', 'last_name', 'email')
        }),
        ('Job Information', {
            'fields': ('role', 'department', 'manager', 'hire_date', 'hourly_rate', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('phone', 'address', 'emergency_contact_name', 'emergency_contact_phone')
        }),
    )