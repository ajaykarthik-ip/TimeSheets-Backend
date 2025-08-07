from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='timesheet',
            name='status',
            field=models.CharField(
                choices=[('draft', 'Draft'), ('submitted', 'Submitted')],
                default='draft',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='timesheet',
            name='submitted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='timesheet',
            unique_together={('employee', 'project', 'date', 'activity_type', 'status')},
        ),
        migrations.AddIndex(
            model_name='timesheet',
            index=models.Index(fields=['status'], name='timesheets_status_idx'),
        ),
    ]