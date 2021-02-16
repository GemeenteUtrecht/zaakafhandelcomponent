# Generated by Django 2.2.16 on 2021-02-16 15:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_merge_20201021_1310'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accessrequest',
            name='comment',
            field=models.CharField(blank=True, help_text='Comment provided by the handler', max_length=1000, verbose_name='comment'),
        ),
        migrations.AlterField(
            model_name='accessrequest',
            name='end_date',
            field=models.DateField(blank=True, help_text='End date of the granted access', null=True, verbose_name='end date'),
        ),
        migrations.AlterField(
            model_name='accessrequest',
            name='result',
            field=models.CharField(blank=True, choices=[('approve', 'approved'), ('reject', 'rejected')], help_text='Result of the access request', max_length=50, verbose_name='result'),
        ),
        migrations.AlterField(
            model_name='accessrequest',
            name='start_date',
            field=models.DateField(blank=True, help_text='Start date of the granted access', null=True, verbose_name='start date'),
        ),
    ]
