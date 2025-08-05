from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/employees/', include('employees.urls')),
    path('api/projects/', include('projects.urls')),  # Added projects URLs
    path('api/timesheets/', include('timesheets.urls')),  # Added timesheets URLs

]