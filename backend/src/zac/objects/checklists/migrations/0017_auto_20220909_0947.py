# Generated by Django 3.2.12 on 2022-09-09 09:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("checklists", "0016_auto_20220909_0946"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="checklistanswer",
            name="checklist",
        ),
        migrations.RemoveField(
            model_name="checklistanswer",
            name="group_assignee",
        ),
        migrations.RemoveField(
            model_name="checklistanswer",
            name="user_assignee",
        ),
        migrations.RemoveField(
            model_name="checklistquestion",
            name="checklisttype",
        ),
        migrations.RemoveField(
            model_name="questionchoice",
            name="question",
        ),
    ]
