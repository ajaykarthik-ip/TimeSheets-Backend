from django.urls import path
from . import views

urlpatterns = [
    # CRUD operations
    path('', views.project_list_create, name='project-list-create'),
    path('<int:pk>/', views.project_detail, name='project-detail'),
    
    # Helper endpoints
    path('choices/', views.project_choices, name='project-choices'),
    path('active/', views.active_projects_list, name='active-projects'),
    path('debug/', views.debug_project_create, name='debug-project-create'),
]