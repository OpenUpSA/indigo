# Generated by Django 2.2.12 on 2020-05-16 12:33

import json
import logging
from reversion.models import Version

from django.contrib.contenttypes.models import ContentType
from django.db import migrations

from indigo_api.data_migrations.akn3 import AKNeId

from cobalt import Act

log = logging.getLogger(__name__)


def update_xml(xml, doc=None):
    # eg: "section-1" => "sec_1"
    cobalt_doc = Act(xml)
    AKNeId().migrate_act(cobalt_doc, doc)

    return cobalt_doc.to_xml().decode("utf-8")


def forward(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Document = apps.get_model("indigo_api", "Document")
    ct_doc = ContentType.objects.get_for_model(Document)

    for document in Document.objects.using(db_alias).all():
        log.info(f"Migrating document: {document.pk}")
        document.document_xml = update_xml(document.document_xml, document)
        document.save()

        # Update historical Document versions
        for version in Version.objects.filter(content_type=ct_doc.pk)\
                .filter(object_id=document.pk).using(db_alias).all():
            log.info(f"Migrating document version: {version.pk}")
            data = json.loads(version.serialized_data)
            data[0]['fields']['document_xml'] = update_xml(data[0]['fields']['document_xml'])
            version.serialized_data = json.dumps(data)
            version.save()


class Migration(migrations.Migration):

    dependencies = [
        ('indigo_api', '0131_migrate_namespaces'),
    ]

    operations = [
        migrations.RunPython(forward),
    ]
