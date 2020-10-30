# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-05-01 08:28
from django.db import migrations


def remove_deleted(apps, schema_editor):
    Work = apps.get_model("indigo_api", "Work")
    db_alias = schema_editor.connection.alias

    for work in Work.objects.filter(deleted=True).using(db_alias).all():
        work.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('indigo_api', '0048_work_commencing_work'),
    ]

    operations = [
        migrations.RunPython(remove_deleted, migrations.RunPython.noop, elidable=True),
    ]
