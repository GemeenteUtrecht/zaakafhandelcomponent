# Generated by Django 3.2.12 on 2024-03-13 13:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('zaak', models.URLField(help_text='URL-reference to the ZAAK in its API', max_length=1000, verbose_name='ZAAK-URL')),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('remarks', models.TextField(blank=True, verbose_name='remarks')),
                ('status', models.CharField(choices=[('on_going', 'On-going'), ('finished', 'Finished')], default='on_going', max_length=50, verbose_name='status')),
                ('document', models.URLField(blank=True, help_text='Document in the Documents API.', max_length=1000, verbose_name='document URL')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activities_created', to=settings.AUTH_USER_MODEL)),
                ('group_assignee', models.ForeignKey(blank=True, help_text='Group responsible for managing this activity.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.group', verbose_name='group assignee')),
                ('user_assignee', models.ForeignKey(blank=True, help_text='Person responsible for managing this activity.', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='user assignee')),
            ],
            options={
                'verbose_name': 'activity',
                'verbose_name_plural': 'activities',
                'unique_together': {('zaak', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notes', models.TextField(verbose_name='notes')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='activities.activity')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='events_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'activity event',
                'verbose_name_plural': 'activity events',
            },
        ),
    ]
