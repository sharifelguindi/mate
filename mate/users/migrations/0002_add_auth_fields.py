# Generated manually for user authentication fields

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='auth_method',
            field=models.CharField(
                choices=[('local', 'Local Password'), ('sso', 'Single Sign-On')],
                default='local',
                help_text='How this user authenticates',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                help_text='User who created this account',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_users',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='force_password_change',
            field=models.BooleanField(
                default=False,
                help_text='Force password change on next login',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='password_changed_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Last password change timestamp',
                null=True,
            ),
        ),
        migrations.AlterModelTable(
            name='user',
            table='users',
        ),
    ]
