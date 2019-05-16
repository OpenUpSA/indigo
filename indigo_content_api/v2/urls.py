from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter

import indigo_content_api.v1.views as v1_views
import views as v2_views

router = DefaultRouter(trailing_slash=False)
router.register(r'countries', v1_views.CountryViewSet, base_name='country')

urlpatterns = [
    url(r'^', include(router.urls)),

    # --- public content API ---
    # viewing a specific document identified by FRBR URI fragment,
    # this requires at least 4 components in the FRBR URI,
    # starting with the two-letter country code
    #
    # eg. /akn/za/act/2007/98
    url(r'^akn/(?P<frbr_uri>[a-z]{2}[-/].*)$', v2_views.PublishedDocumentDetailViewV2.as_view({'get': 'get'}), name='published-document-detail'),
    url(r'^search/(?P<country>[a-z]{2})$', v1_views.PublishedDocumentSearchView.as_view(), name='public-search'),
]
