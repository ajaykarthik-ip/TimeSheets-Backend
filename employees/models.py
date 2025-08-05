from django.db import models
from django.contrib.auth.models import User

class Employee(models.Model):
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('developer', 'Developer'),
        ('designer', 'Designer'),
        ('analyst', 'Analyst'),
        ('tester', 'Tester'),
        ('intern', 'Intern'),
        ('admin', 'Admin'),
    ]
    
    DEPARTMENT_CHOICES = [
        ('engineering', 'Engineering'),
        ('design', 'Design'),
        ('marketing', 'Marketing'),
        ('sales', 'Sales'),
        ('hr', 'Human Resources'),
        ('finance', 'Finance'),
        ('operations', 'Operations'),
    ]
    
    # Auto-generated employee ID
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='subordinates')
    address = models.TextField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['employee_id']
        
    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = self.generate_employee_id()
        super().save(*args, **kwargs)
    
    def generate_employee_id(self):
        """Generate employee ID in format: EMP001, EMP002, etc."""
        last_employee = Employee.objects.filter(
            employee_id__startswith='EMP'
        ).order_by('employee_id').last()
        
        if last_employee:
            # Extract number from last employee ID (e.g., 'EMP001' -> 1)
            try:
                last_number = int(last_employee.employee_id[3:])
                new_number = last_number + 1
            except (ValueError, IndexError):
                new_number = 1
        else:
            new_number = 1
        
        # Format with leading zeros (EMP001, EMP002, etc.)
        return f"EMP{new_number:03d}"
    
    def __str__(self):
        return f"{self.employee_id} - {self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"