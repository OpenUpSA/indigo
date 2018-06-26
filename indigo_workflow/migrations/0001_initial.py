# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-06-26 13:45
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('viewflow', '0006_i18n'),
        ('indigo_app', '0009_publication'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImplicitPlaceProcess',
            fields=[
                ('process_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='viewflow.Process')),
                ('approved', models.BooleanField(default=False)),
                ('notes', models.TextField(null=True)),
                ('country', models.ForeignKey(help_text=b'Country to list works for', on_delete=django.db.models.deletion.CASCADE, related_name='list_works_tasks', to='indigo_app.Country')),
                ('locality', models.ForeignKey(help_text=b'Locality to list works for', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='list_works_tasks', to='indigo_app.Locality')),
            ],
            options={
                'abstract': False,
            },
            bases=('viewflow.process',),
        ),
    ]
