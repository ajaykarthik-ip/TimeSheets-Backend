# Generated migration file
# Save this as: employees/migrations/0005_update_structure.py

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0004_alter_employee_role'),
    ]

    operations = [
        # Add designation field
        migrations.AddField(
            model_name='employee',
            name='designation',
            field=models.CharField(
                choices=[
                    ('managing_partner', 'Managing Partner'),
                    ('head_of_engineering', 'Head of Engineering'),
                    ('head_of_sales', 'Head of Sales'),
                    ('business_operations_manager', 'Business Operations Manager'),
                    ('business_development_manager', 'Business Development Manager'),
                    ('business_consultant', 'Business Consultant'),
                    ('business_analyst_intern', 'Business Analyst Intern'),
                    ('ai_architect', 'AI Architect'),
                    ('principal_engineer', 'Principal Engineer'),
                    ('engineering_tech_lead', 'Engineering Tech Lead'),
                    ('solutions_architect', 'Solutions Architect'),
                    ('sr_software_engineer', 'Sr Software Engineer'),
                    ('software_engineer', 'Software Engineer'),
                    ('ai_engineer', 'AI Engineer'),
                    ('software_developer_intern', 'Software Developer Intern'),
                    ('design_lead', 'Design Lead'),
                    ('senior_designer', 'Senior Designer'),
                    ('designer', 'Designer'),
                    ('sr_qa_engineer', 'Sr QA Engineer'),
                    ('qa_engineer', 'QA Engineer'),
                    ('qa_intern', 'QA Intern'),
                    ('hr_admin_manager', 'HR & Admin Manager'),
                ],
                db_index=True,
                default='software_engineer',  # Set a default
                max_length=50
            ),
        ),
        
        # Update department field choices
        migrations.AlterField(
            model_name='employee',
            name='department',
            field=models.CharField(
                choices=[
                    ('executive_leadership', 'Executive / Leadership'),
                    ('business_consulting', 'Business / Consulting'),
                    ('engineering_development', 'Engineering / Development'),
                    ('design', 'Design'),
                    ('quality_assurance', 'Quality Assurance'),
                    ('hr_admin', 'HR & Admin'),
                ],
                db_index=True,
                max_length=30,
            ),
        ),
        
        # Update role field choices
        migrations.AlterField(
            model_name='employee',
            name='role',
            field=models.CharField(
                choices=[
                    ('admin', 'Admin'),
                    ('mobiux_employee', 'Mobiux Employee'),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        
        # Add new index for designation
        migrations.AddIndex(
            model_name='employee',
            index=models.Index(fields=['designation', 'is_active'], name='employees_e_designa_f8a9b2_idx'),
        ),
    ]