from django.urls import path
from . import views

urlpatterns = [
    # CRUD operations
    path('', views.timesheet_list_create, name='timesheet-list-create'),
    path('<int:pk>/', views.timesheet_detail, name='timesheet-detail'),
    
    # User-specific endpoints
    path('my-timesheets/', views.my_timesheets, name='my-timesheets'),
    path('current-user/', views.current_user_employee, name='current-user-employee'),
    
    # Analytics and summary
    path('summary/', views.timesheet_summary, name='timesheet-summary'),
    
    # Helper endpoints
    path('project/<int:project_id>/activities/', views.project_activities, name='project-activities'),
    
    # Debug endpoint
    path('debug/', views.debug_timesheet_create, name='debug-timesheet-create'),
]