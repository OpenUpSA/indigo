# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-05-24 15:55
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('indigo_api', '0096_auto_20190424_1245'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workproperty',
            name='work',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='raw_properties', to='indigo_api.Work'),
        ),
    ]
