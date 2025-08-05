from django.db import models
import json

class Project(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=200)
    billable = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    activity_types = models.TextField(
        help_text='JSON array of activity types specific to this project',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
    def get_activity_types(self):
        """Return activity types as a Python list"""
        if self.activity_types:
            try:
                return json.loads(self.activity_types)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_activity_types(self, activity_list):
        """Set activity types from a Python list"""
        if activity_list:
            self.activity_types = json.dumps(activity_list)
        else:
            self.activity_types = None