from django.contrib import admin
from .models import Project

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'billable', 'status', 'created_at', 'updated_at']
    list_filter = ['billable', 'status', 'created_at']
    search_fields = ['name']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'billable', 'status')
        }),
        ('Activity Types', {
            'fields': ('activity_types',),
            'description': 'JSON array of activity types (e.g., ["Development", "Testing", "Design"])'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']