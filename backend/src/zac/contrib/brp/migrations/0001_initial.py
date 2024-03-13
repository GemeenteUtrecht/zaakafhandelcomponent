# Generated by Django 3.2.12 on 2024-03-13 13:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('zgw_consumers', '0017_auto_20240313_1347'),
    ]

    operations = [
        migrations.CreateModel(
            name='BRPConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service', models.ForeignKey(limit_choices_to={'api_type': 'orc'}, null=True, on_delete=django.db.models.deletion.SET_NULL, to='zgw_consumers.service')),
            ],
            options={
                'verbose_name': 'BRP configuration',
            },
        ),
    ]
