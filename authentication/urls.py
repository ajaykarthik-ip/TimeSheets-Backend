from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.user_profile, name='user-profile'),
    path('csrf/', views.csrf_token, name='csrf-token'),
    path('google-login/', views.google_login_view, name='google-login'), 
    path('cors-test/', views.cors_test, name='cors-test'), 
]