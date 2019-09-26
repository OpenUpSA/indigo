# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-04-16 18:53
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('indigo_api', '0044_work_parent_work'),
    ]

    operations = [
        migrations.CreateModel(
            name='Amendment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(help_text=b'Date of the amendment')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amended_work', models.ForeignKey(help_text=b'Work amended.', on_delete=django.db.models.deletion.CASCADE, related_name='amendments', to='indigo_api.Work')),
                ('amending_work', models.ForeignKey(help_text=b'Work making the amendment.', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='indigo_api.Work')),
                ('created_by_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('updated_by_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
