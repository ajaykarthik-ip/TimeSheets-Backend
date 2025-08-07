from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import Project
from .serializers import ProjectSerializer, ProjectListSerializer
from django.core.paginator import Paginator
from django.db.models import Prefetch

@csrf_exempt
def project_list_create(request):
    """
    GET: List all projects
    POST: Create new project
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.method == 'GET':
        projects = Project.objects.all()
        
        # Filter by status if provided
        status_filter = request.GET.get('status')
        if status_filter:
            projects = projects.filter(status=status_filter)
        
        # Filter by billable if provided
        billable = request.GET.get('billable')
        if billable is not None:
            projects = projects.filter(billable=billable.lower() == 'true')
        
        # Search by name
        search = request.GET.get('search')
        if search:
            projects = projects.filter(name__icontains=search)
        
        serializer = ProjectListSerializer(projects, many=True)
        return JsonResponse({
            'count': projects.count(),
            'projects': serializer.data
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            serializer = ProjectSerializer(data=data)
            if serializer.is_valid():
                try:
                    with transaction.atomic():
                        project = serializer.save()
                    return JsonResponse({
                        'message': 'Project created successfully',
                        'project': ProjectSerializer(project).data
                    }, status=201)
                except Exception as e:
                    return JsonResponse({
                        'error': 'Failed to create project',
                        'details': str(e)
                    }, status=400)
            return JsonResponse(serializer.errors, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def project_detail(request, pk):
    """
    GET: Retrieve project by ID
    PUT: Update project
    DELETE: Delete project
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return JsonResponse({'error': 'Project not found'}, status=404)
    
    if request.method == 'GET':
        serializer = ProjectSerializer(project)
        return JsonResponse({
            'project': serializer.data
        })
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            serializer = ProjectSerializer(project, data=data, partial=True)
            if serializer.is_valid():
                try:
                    with transaction.atomic():
                        project = serializer.save()
                    return JsonResponse({
                        'message': 'Project updated successfully',
                        'project': ProjectSerializer(project).data
                    })
                except Exception as e:
                    return JsonResponse({
                        'error': 'Failed to update project',
                        'details': str(e)
                    }, status=400)
            return JsonResponse(serializer.errors, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        try:
            with transaction.atomic():
                project.delete()
            return JsonResponse({
                'message': 'Project deleted successfully'
            }, status=204)
        except Exception as e:
            return JsonResponse({
                'error': 'Failed to delete project',
                'details': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_choices(request):
    """Get choices for dropdowns"""
    return Response({
        'statuses': dict(Project.STATUS_CHOICES)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_projects_list(request):
    """Get list of active projects for dropdowns"""
    projects = Project.objects.filter(status='active').values('id', 'name', 'billable')
    
    return Response({
        'projects': list(projects)
    })

@csrf_exempt
def debug_project_create(request):
    """Debug endpoint to see what's happening"""
    if request.method == 'POST':
        try:
            print("Raw request body:", request.body)
            data = json.loads(request.body)
            print("Parsed data:", data)
            
            serializer = ProjectSerializer(data=data)
            print("Serializer valid:", serializer.is_valid())
            
            if not serializer.is_valid():
                print("Serializer errors:", serializer.errors)
                return JsonResponse({
                    'validation_errors': serializer.errors,
                    'received_data': data
                }, status=400)
            
            return JsonResponse({'message': 'Validation passed'})
            
        except Exception as e:
            print("Exception:", str(e))
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)