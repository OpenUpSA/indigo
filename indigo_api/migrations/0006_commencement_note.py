# Generated by Django 2.2.12 on 2021-03-18 12:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indigo_api', '0005_block_tasks'),
    ]

    operations = [
        migrations.AddField(
            model_name='commencement',
            name='note',
            field=models.TextField(blank=True, help_text='Usually a reference to a provision of the commenced work or a commencing work, if there is a commencement but the date is open to interpretation', max_length=1024, null=True),
        ),
    ]
