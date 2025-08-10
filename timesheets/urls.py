from django.urls import path
from . import views

urlpatterns = [
    # Basic CRUD operations
    path('', views.timesheet_list_create, name='timesheet-list-create'),
    path('<int:pk>/', views.timesheet_detail, name='timesheet-detail'),
    
    # Admin-specific endpoints
    path('admin/all/', views.admin_all_timesheets, name='admin-all-timesheets'),
    
    # User-specific endpoints
    path('my-timesheets/', views.my_timesheets, name='my-timesheets'),
    path('current-user/', views.current_user_employee, name='current-user-employee'),
    path('drafts/', views.drafts_list, name='drafts-list'),
    
    # INDIVIDUAL SUBMIT DISABLED - kept for error message
    path('<int:pk>/submit/', views.submit_timesheet, name='submit-timesheet-disabled'),
    
    # BULK/WEEKLY submission (THE ONLY WAY TO SUBMIT)
    path('submit-week/', views.submit_week_timesheets, name='submit-week'),
    path('week-summary/', views.get_week_summary, name='week-summary'),
    path('validate-week/', views.validate_week_timesheets, name='validate-week'),
    path('bulk-actions/', views.bulk_timesheet_actions, name='bulk-actions'),
    
    # Analytics and summary
    path('summary/', views.timesheet_summary, name='timesheet-summary'),
    
    # Helper endpoints
    path('project/<int:project_id>/activities/', views.project_activities, name='project-activities'),
    
    # Debug endpoint
    path('debug/', views.debug_timesheet_create, name='debug-timesheet-create'),
]