# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-03-24 11:51
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('indigo_api', '0038_auto_20180324_1116'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='work',
            name='draft',
        ),
    ]