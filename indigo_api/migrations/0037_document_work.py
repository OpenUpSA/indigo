# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-03-24 09:52
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


def create_works(apps, schema_editor):
    Document = apps.get_model("indigo_api", "Document")
    Work = apps.get_model("indigo_api", "Work")
    db_alias = schema_editor.connection.alias

    documents = Document.objects.using(db_alias).values('id', 'frbr_uri', 'title', 'country')
    # works to create
    work_detail = {d['frbr_uri']: (d['title'], d['country']) for d in documents}

    # create them
    works = [Work(frbr_uri=k, title=t, country=c) for k, (t, c) in work_detail.iteritems()]
    Work.objects.using(db_alias).bulk_create(works)


def delete_works(apps, schema_editor):
    Work = apps.get_model("indigo_api", "Work")
    db_alias = schema_editor.connection.alias
    Work.objects.using(db_alias).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('indigo_api', '0036_work'),
    ]

    operations = [
        migrations.RunPython(create_works, delete_works),
        migrations.AddField(
            model_name='document',
            name='work',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='indigo_api.Work', null=True),
            preserve_default=False,
        ),

        # link documents to works
        migrations.RunSQL("UPDATE indigo_api_document d SET work_id = (SELECT id FROM indigo_api_work w WHERE d.frbr_uri = w.frbr_uri LIMIT 1)",
                          migrations.RunSQL.noop),

        # make work column non-null
        migrations.AlterField(
            model_name='document',
            name='work',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='indigo_api.Work', null=False),
        ),
    ]
