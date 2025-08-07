from django.urls import path
from . import views

urlpatterns = [
    # CRUD operations
    path('', views.employee_list_create, name='employee-list-create'),
    path('<int:pk>/', views.employee_detail, name='employee-detail'),
    path('employee-id/<str:employee_id>/', views.employee_by_employee_id, name='employee-by-id'),
    
    # Helper endpoints
    path('choices/', views.employee_choices, name='employee-choices'),
    path('managers/', views.managers_list, name='managers-list'),
    
    # Debug endpoint
    path('debug/', views.debug_employee_create, name='debug-create'),
]