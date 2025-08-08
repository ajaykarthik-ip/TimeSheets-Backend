from django.db import models
from django.contrib.auth.models import User
from django.core.cache import cache

class Employee(models.Model):
    # Simplified role choices - only 2 roles
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('mobiux_employee', 'Mobiux Employee'),
    ]
    
    # Updated department choices - 6 departments
    DEPARTMENT_CHOICES = [
        ('executive_leadership', 'Executive / Leadership'),
        ('business_consulting', 'Business / Consulting'),
        ('engineering_development', 'Engineering / Development'),
        ('design', 'Design'),
        ('quality_assurance', 'Quality Assurance'),
        ('hr_admin', 'HR & Admin'),
    ]
    
    # New designation choices based on your structure
    DESIGNATION_CHOICES = [
        # Executive / Leadership
        ('managing_partner', 'Managing Partner'),
        ('head_of_engineering', 'Head of Engineering'),
        ('head_of_sales', 'Head of Sales'),
        ('business_operations_manager', 'Business Operations Manager'),
        ('business_development_manager', 'Business Development Manager'),
        
        # Business / Consulting
        ('business_consultant', 'Business Consultant'),
        ('business_analyst_intern', 'Business Analyst Intern'),
        
        # Engineering / Development
        ('ai_architect', 'AI Architect'),
        ('principal_engineer', 'Principal Engineer'),
        ('engineering_tech_lead', 'Engineering Tech Lead'),
        ('solutions_architect', 'Solutions Architect'),
        ('sr_software_engineer', 'Sr Software Engineer'),
        ('software_engineer', 'Software Engineer'),
        ('ai_engineer', 'AI Engineer'),
        ('software_developer_intern', 'Software Developer Intern'),
        
        # Design
        ('design_lead', 'Design Lead'),
        ('senior_designer', 'Senior Designer'),
        ('designer', 'Designer'),
        
        # Quality Assurance
        ('sr_qa_engineer', 'Sr QA Engineer'),
        ('qa_engineer', 'QA Engineer'),
        ('qa_intern', 'QA Intern'),
        
        # HR & Admin
        ('hr_admin_manager', 'HR & Admin Manager'),
    ]
    
    # Auto-generated employee ID
    employee_id = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee')
    first_name = models.CharField(max_length=50, db_index=True)
    last_name = models.CharField(max_length=50, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    department = models.CharField(max_length=30, choices=DEPARTMENT_CHOICES, db_index=True)
    designation = models.CharField(max_length=50, choices=DESIGNATION_CHOICES, db_index=True)  # NEW FIELD
    hire_date = models.DateField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='subordinates')
    address = models.TextField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['employee_id']
        indexes = [
            # Updated indexes for new structure
            models.Index(fields=['email']),
            models.Index(fields=['department', 'is_active']),
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['designation', 'is_active']),  # NEW INDEX
            models.Index(fields=['manager', 'is_active']),
            models.Index(fields=['is_active', 'hire_date']),
            models.Index(fields=['employee_id', 'is_active']),
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['-created_at']),
        ]
        
    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = self.generate_employee_id()
        
        # Clear related cache when employee is saved
        if self.pk:
            cache.delete(f'employee_{self.pk}')
            cache.delete('managers_list')
            cache.delete('employee_choices')
            
        super().save(*args, **kwargs)
    
    def generate_employee_id(self):
        """Generate employee ID in format: EMP001, EMP002, etc."""
        from django.db import transaction
        
        with transaction.atomic():
            last_employee = Employee.objects.filter(
                employee_id__startswith='EMP'
            ).order_by('employee_id').last()
            
            if last_employee:
                try:
                    last_number = int(last_employee.employee_id[3:])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            
            return f"EMP{new_number:03d}"
    
    def __str__(self):
        return f"{self.employee_id} - {self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @classmethod
    def get_active_managers(cls):
        """Cached method to get active managers (admin role only)"""
        cache_key = 'active_managers'
        managers = cache.get(cache_key)
        
        if managers is None:
            managers = cls.objects.filter(
                role='admin',  # Only admin role can be managers now
                is_active=True
            ).values('id', 'employee_id', 'first_name', 'last_name').order_by('first_name')
            cache.set(cache_key, list(managers), 1800)
        
        return managers
    
    @classmethod
    def get_choices(cls):
        """Cached method to get role, department, and designation choices"""
        cache_key = 'employee_choices'
        choices = cache.get(cache_key)
        
        if choices is None:
            choices = {
                'roles': dict(cls.ROLE_CHOICES),
                'departments': dict(cls.DEPARTMENT_CHOICES),
                'designations': dict(cls.DESIGNATION_CHOICES)  # NEW
            }
            cache.set(cache_key, choices, 3600)
        
        return choices