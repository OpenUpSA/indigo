from lxml.etree import LxmlError

from rest_framework import serializers, renderers
from rest_framework.reverse import reverse
from rest_framework.exceptions import ValidationError
from indigo_an.act import Act

from .models import Document

class DocumentSerializer(serializers.HyperlinkedModelSerializer):
    publication_date = serializers.DateField(required=False)

    body = serializers.CharField(required=False, write_only=True)
    """ A write-only field for setting the body of the document. """

    body_url = serializers.SerializerMethodField()
    """ A read-only URL for the body of the document. The body isn't included in the
    document description because it could be huge. """

    content = serializers.CharField(required=False, write_only=True)
    """ A write-only field for setting the entire XML content of the document. """

    content_url = serializers.SerializerMethodField()
    """ A URL for the entire content of the document. The content isn't included in the
    document description because it could be huge. """

    published_url = serializers.SerializerMethodField()
    """ Public URL of a published document. """

    class Meta:
        model = Document
        fields = (
                # readonly, url is part of the rest framework
                'id', 'url',

                'frbr_uri', 'draft', 'created_at', 'updated_at',
                'title', 'country', 'number', 'year', 'nature',
                'publication_date', 'publication_name', 'publication_number',

                'body', 'body_url',
                'content', 'content_url',

                'published_url',
                )
        read_only_fields = ('number', 'nature', 'created_at', 'updated_at', 'year')

    def get_body_url(self, doc):
        return reverse('document-body', request=self.context['request'], kwargs={'pk': doc.pk})

    def get_content_url(self, doc):
        return reverse('document-content', request=self.context['request'], kwargs={'pk': doc.pk})

    def get_published_url(self, doc):
        if doc.draft:
            return None
        else:
            return reverse('published-document-detail', request=self.context['request'], kwargs={'frbr_uri': doc.frbr_uri[1:]})

    def validate_content(self, value):
        try:
            Act(value)
        except LxmlError as e:
            raise ValidationError("Invalid XML: %s" % e.message)
        return value

    def to_representation(self, instance):
        rep = super(DocumentSerializer, self).to_representation(instance)
        rep['toc'] = [t.as_dict() for t in instance.doc.table_of_contents()]
        return rep


class AkomaNtosoRenderer(renderers.XMLRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        return data
