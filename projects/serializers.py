from rest_framework import serializers
from .models import Project
import json

class ProjectSerializer(serializers.ModelSerializer):
    activity_types_list = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=False,
        help_text="List of activity types for this project"
    )
    activity_types_display = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'billable', 'status', 'activity_types', 
            'activity_types_list', 'activity_types_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'activity_types', 'activity_types_display']
    
    def get_activity_types_display(self, obj):
        """Return activity types as a list for display"""
        return obj.get_activity_types()
    
    def create(self, validated_data):
        activity_types_list = validated_data.pop('activity_types_list', [])
        project = Project.objects.create(**validated_data)
        if activity_types_list:
            project.set_activity_types(activity_types_list)
            project.save()
        return project
    
    def update(self, instance, validated_data):
        activity_types_list = validated_data.pop('activity_types_list', None)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update activity types if provided
        if activity_types_list is not None:
            instance.set_activity_types(activity_types_list)
        
        instance.save()
        return instance

class ProjectListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    activity_types_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'billable', 'status', 'status_display',
            'activity_types_display', 'created_at', 'updated_at'
        ]
    
    def get_activity_types_display(self, obj):
        return obj.get_activity_types()