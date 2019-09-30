# -*- coding: utf-8 -*-
import re
import csv
import io
import logging

from cobalt import FrbrUri
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.conf import settings
import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

from indigo.plugins import LocaleBasedMatcher, plugins
from indigo_api.models import Subtype, Work, WorkProperty, PublicationDocument, Task, Amendment
from indigo_api.signals import work_changed


class RowValidationFormBase(forms.Form):
    country = forms.CharField()
    locality = forms.CharField(required=False)
    title = forms.CharField()
    primary_work = forms.CharField(required=False)
    subtype = forms.CharField(required=False, validators=[
        RegexValidator(r'^\S+$', 'No spaces allowed.')
    ])
    number = forms.CharField(validators=[
        RegexValidator(r'^[a-zA-Z0-9-]+$', 'No spaces or punctuation allowed (use \'-\' for spaces).')
    ])
    year = forms.CharField(validators=[
        RegexValidator(r'\d{4}', 'Must be a year (yyyy).')
    ])
    publication_name = forms.CharField(required=False)
    publication_number = forms.CharField(required=False)
    publication_date = forms.DateField(error_messages={'invalid': 'Date format should be yyyy-mm-dd.'})
    assent_date = forms.DateField(required=False, error_messages={'invalid': 'Date format should be yyyy-mm-dd.'})
    commencement_date = forms.DateField(required=False, error_messages={'invalid': 'Date format should be yyyy-mm-dd.'})
    principal = forms.BooleanField(required=False)
    commenced_by = forms.CharField(required=False)
    amends = forms.CharField(required=False)
    repealed_by = forms.CharField(required=False)

    def clean_title(self):
        title = self.cleaned_data.get('title')
        return re.sub('[\u2028 ]+', ' ', title)


@plugins.register('bulk-creator')
class BaseBulkCreator(LocaleBasedMatcher):
    """ Create works in bulk from a google sheets spreadsheet.
    Subclass RowValidationFormBase() and get_row_validation_form() to check / raise errors for different fields.
    """
    locale = (None, None, None)
    """ The locale this bulk creator is suited for, as ``(country, language, locality)``.
    """
    extra_properties = {}

    log = logging.getLogger(__name__)

    _service = None
    _gsheets_secret = None

    GSHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    def gsheets_id_from_url(self, url):
        match = re.match(r'^https://docs.google.com/spreadsheets/d/(\S+)/', url)
        if match:
            return match.group(1)

    def get_datatable(self, spreadsheet_url, sheet_name):
        spreadsheet_id = self.gsheets_id_from_url(spreadsheet_url)
        if not spreadsheet_id:
            raise ValidationError("Unable to extract key from Google Sheets URL")

        if self.is_gsheets_enabled:
            return self.get_datatable_gsheets(spreadsheet_id, sheet_name)
        else:
            return self.get_datatable_csv(spreadsheet_id)

    def get_datatable_csv(self, spreadsheet_id):
        try:
            url = 'https://docs.google.com/spreadsheets/d/%s/export?format=csv' % spreadsheet_id
            response = requests.get(url, timeout=5)
            response.raise_for_status()
        except requests.RequestException as e:
            raise ValidationError("Error talking to Google Sheets: %s" % str(e))

        reader = csv.reader(io.StringIO(response.content.decode('utf-8')))
        rows = list(reader)

        if not rows or not rows[0]:
            raise ValidationError(
                "Your sheet did not import successfully; "
                "please check that you have link sharing ON (Anyone with the link)."
            )
        return rows

    @property
    def is_gsheets_enabled(self):
        return bool(settings.INDIGO.get('GSHEETS_API_CREDS'))

    def get_spreadsheet_sheets(self, spreadsheet_id):
        if self.is_gsheets_enabled:
            try:
                metadata = self.gsheets_client.spreadsheets()\
                    .get(spreadsheetId=spreadsheet_id)\
                    .execute()
                return metadata['sheets']
            except HttpError as e:
                self.log.warning("Error getting data from google sheets for {}".format(spreadsheet_id), exc_info=e)
                raise ValueError(str(e))

        return []

    def get_datatable_gsheets(self, spreadsheet_id, sheet_name):
        """ Fetch a datatable from a Google Sheets spreadsheet, using the given URL and sheet
        index (tab index).
        """
        try:
            result = self.gsheets_client\
                .spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=sheet_name)\
                .execute()
        except HttpError as e:
            self.log.warning("Error getting data from google sheets for {}".format(spreadsheet_id), exc_info=e)
            raise ValidationError("Unable to access spreadsheet. Is the URL correct and have you shared it with {}?".format(
                self._gsheets_secret['client_email'],
            ))

        rows = result.get('values', [])
        if not rows or not rows[0]:
            raise ValidationError("There doesn't appear to be data in sheet {} of {}".format(sheet_name, spreadsheet_id))
        return rows

    @property
    def gsheets_client(self):
        if not self._service:
            if not self._gsheets_secret:
                self._gsheets_secret = settings.INDIGO['GSHEETS_API_CREDS']
            credentials = service_account.Credentials.from_service_account_info(self._gsheets_secret, scopes=self.GSHEETS_SCOPES)
            self._service = build('sheets', 'v4', credentials=credentials)
        return self._service

    def get_row_validation_form(self, row_data):
        return RowValidationFormBase(row_data)

    def create_works(self, view, table, dry_run, workflow, user):
        self.workflow = workflow
        self.user = user

        works = []

        # clean up headers
        headers = [h.split(' ')[0].lower() for h in table[0]]

        # transform rows into list of dicts for easy access
        rows = [
            {header: row[i] for i, header in enumerate(headers) if header and i < len(row)}
            for row in table[1:]
        ]

        for idx, row in enumerate(rows):
            # ignore if it's blank or explicitly marked 'ignore' in the 'ignore' column
            if row.get('ignore') or not [val for val in row.values() if val]:
                continue

            works.append(self.create_work(view, row, idx, dry_run))

        if not dry_run:
            for info in works:
                if info['status'] == 'success':
                    if info.get('commenced_by'):
                        self.link_commencement(info['work'], info)

                    if info.get('repealed_by'):
                        self.link_repeal(info['work'], info)

                    if info.get('primary_work'):
                        self.link_parent_work(info['work'], info)

                if info['status'] != 'error' and info.get('amends'):
                    # this will check duplicate works as well
                    # (they won't overwrite the existing works but the amendments will be linked)
                    self.link_amendment(info['work'], info)

        return works

    def create_work(self, view, row, idx, dry_run):
        # copy all row details
        info = row
        info['row'] = idx + 2

        row = self.validate_row(view, row)

        if row.get('errors'):
            info['status'] = 'error'
            info['error_message'] = row['errors']
            return info

        frbr_uri = self.get_frbr_uri(row)

        try:
            work = Work.objects.get(frbr_uri=frbr_uri)
            info['work'] = work
            info['status'] = 'duplicate'
            info['amends'] = row.get('amends') or None
            info['commencement_date'] = row.get('commencement_date') or None

        except Work.DoesNotExist:
            work = Work()

            work.frbr_uri = frbr_uri
            work.country = view.country
            work.locality = view.locality
            work.title = row.get('title')
            work.publication_name = row.get('publication_name')
            work.publication_number = row.get('publication_number')
            work.publication_date = row.get('publication_date')
            work.commencement_date = row.get('commencement_date')
            work.assent_date = row.get('assent_date')
            work.stub = not row.get('principal')
            work.created_by_user = view.request.user
            work.updated_by_user = view.request.user

            try:
                work.full_clean()
                if not dry_run:
                    work.save_with_revision(view.request.user)

                    # signals
                    work_changed.send(sender=work.__class__, work=work, request=view.request)

                    # info for links, extra properties
                    pub_doc_params = {
                        'date': row.get('publication_date'),
                        'number': work.publication_number,
                        'publication': work.publication_name,
                        'country': view.country.place_code,
                        'locality': view.locality.code if view.locality else None,
                    }
                    info['params'] = pub_doc_params

                    self.add_extra_properties(work, info)
                    self.link_publication_document(work, info)

                    if not work.stub:
                        self.create_task(work, info, task_type='import')

                info['work'] = work
                info['status'] = 'success'

            except ValidationError as e:
                info['status'] = 'error'
                if hasattr(e, 'message_dict'):
                    info['error_message'] = ' '.join(
                        ['%s: %s' % (f, '; '.join(errs)) for f, errs in e.message_dict.items()]
                    )
                else:
                    info['error_message'] = str(e)

        return info

    def validate_row(self, view, row):
        row_country = row.get('country')
        row_locality = row.get('locality')
        row_subtype = row.get('subtype')
        available_subtypes = [s.abbreviation for s in Subtype.objects.all()]

        row_data = row
        row_data['country'] = view.country.code
        row_data['locality'] = view.locality.code if view.locality else None
        form = self.get_row_validation_form(row_data)

        # Extra validation
        # - if the subtype hasn't been registered
        if row_subtype and row_subtype.lower() not in available_subtypes:
            form.add_error('subtype', 'The subtype given ({}) doesn\'t match any in the list: {}.'
                           .format(row.get('subtype'), ", ".join(available_subtypes)))

        # - if the country is missing or doesn't match
        if not row_country or view.country.code != row_country.lower():
            form.add_error('country', 'The country code given in the spreadsheet ({}) '
                                      'doesn\'t match the code for the country you\'re working in ({}).'
                                      .format(row_country or 'Missing', view.country.code.upper()))

        # - if you're working on the country level but the spreadsheet gives a locality
        #   or the locality doesn't match
        if row_locality:
            if not view.locality:
                form.add_error('locality', 'The spreadsheet gives a locality code ({}), '
                                           'but you\'re working in a country ({}).'
                                           .format(row_locality, view.country.code.upper()))

            elif not view.locality.code == row_locality.lower():
                form.add_error('locality', 'The locality code given in the spreadsheet ({}) '
                                           'doesn\'t match the code for the locality you\'re working in ({}).'
                                           .format(row_locality, view.locality.code.upper()))

        # - if you're working on the locality level but the spreadsheet doesn't give one
        if not row_locality and view.locality:
            form.add_error('locality', 'The spreadsheet doesn\'t give a locality code, '
                                       'but you\'re working in {} ({}).'
                                       .format(view.locality, view.locality.code.upper()))

        errors = form.errors
        row = form.cleaned_data
        row['errors'] = errors
        return row

    def get_frbr_uri(self, row):
        frbr_uri = FrbrUri(country=row.get('country'),
                           locality=row.get('locality'),
                           doctype='act',
                           subtype=row.get('subtype'),
                           date=row.get('year'),
                           number=row.get('number'),
                           actor=None)

        return frbr_uri.work_uri().lower()

    def add_extra_properties(self, work, info):
        for extra_property in self.extra_properties.keys():
            if info.get(extra_property):
                new_prop = WorkProperty(work=work, key=extra_property, value=info.get(extra_property))
                new_prop.save()

    def link_publication_document(self, work, info):
        params = info.get('params')
        locality_code = self.locality.code if self.locality else None
        finder = plugins.for_locale('publications', self.country.code, None, locality_code)

        if not finder or not params.get('date'):
            return self.create_task(work, info, task_type='link-publication-document')

        publications = finder.find_publications(params)

        if len(publications) != 1:
            return self.create_task(work, info, task_type='link-publication-document')

        pub_doc_details = publications[0]
        pub_doc = PublicationDocument()
        pub_doc.work = work
        pub_doc.file = None
        pub_doc.trusted_url = pub_doc_details.get('url')
        pub_doc.size = pub_doc_details.get('size')
        pub_doc.save()

    def link_commencement(self, work, info):
        # if the work is `commenced_by` something, try linking it
        # make a task if this fails
        title = info['commenced_by']
        work = info['work']
        commencing_work = self.find_work_by_title(title)
        if not commencing_work:
            return self.create_task(work, info, task_type='link-commencement')

        work.commencing_work = commencing_work
        try:
            work.save_with_revision(self.user)
        except ValidationError:
            self.create_task(work, info, task_type='link-commencement')

    def link_repeal(self, work, info):
        # if the work is `repealed_by` something, try linking it
        # make a task if this fails
        # (either because the work isn't found or because the repeal date isn't right,
        # which could be because it doesn't exist or because it's in the wrong format)
        repealing_work = self.find_work_by_title(info['repealed_by'])
        if not repealing_work:
            return self.create_task(work, info, task_type='link-repeal')

        repeal_date = repealing_work.commencement_date
        if not repeal_date:
            return self.create_task(work, info, task_type='link-repeal')

        work.repealed_by = repealing_work
        work.repealed_date = repeal_date

        try:
            work.save_with_revision(self.user)
        except ValidationError:
            self.create_task(work, info, task_type='link-repeal')

    def link_parent_work(self, work, info):
        # if the work has a `primary_work`, try linking it
        # make a task if this fails
        parent_work = self.find_work_by_title(info['primary_work'])
        if not parent_work:
            return self.create_task(work, info, task_type='link-primary-work')

        work.parent_work = parent_work

        try:
            work.save_with_revision(self.user)
        except ValidationError:
            self.create_task(work, info, task_type='link-primary-work')

    def link_amendment(self, work, info):
        # if the work `amends` something, try linking it
        # (this will only work if there's only one amendment listed)
        # make a task if this fails
        amended_work = self.find_work_by_title(info['amends'])
        if not amended_work:
            return self.create_task(work, info, task_type='link-amendment')

        date = info.get('commencement_date') or work.commencement_date
        if not date:
            return self.create_task(work, info, task_type='link-amendment')

        try:
            Amendment.objects.get(
                amended_work=amended_work,
                amending_work=work,
                date=date
            )

        except Amendment.DoesNotExist:
            amendment = Amendment()
            amendment.amended_work = amended_work
            amendment.amending_work = work
            amendment.created_by_user = self.user
            amendment.date = date
            amendment.save()

    def create_task(self, work, info, task_type):
        task = Task()

        if task_type == 'link-publication-document':
            task.title = 'Link publication document'
            task.description = '''This work's publication document could not be linked automatically – see row {}.
Find it and upload it manually.'''.format(info['row'])

        elif task_type == 'import':
            task.title = 'Import content'
            task.description = '''Import a point in time for this work; either the initial publication or a later consolidation.
Make sure the document's expression date is correct.'''

        elif task_type == 'link-commencement':
            task.title = 'Link commencement'
            task.description = '''On the spreadsheet, it says that this work is commenced by '{}' – see row {}.

The commencement work could not be linked automatically.
Possible reasons:
– a typo in the spreadsheet
– the commencing work hasn't been imported.

Check the spreadsheet for reference and link it manually.'''.format(info['commenced_by'], info['row'])

        elif task_type == 'link-amendment':
            task.title = 'Link amendment(s)'
            amended_title = info['amends']
            if len(amended_title) > 256:
                amended_title = "".join(amended_title[:256] + ', etc')
            task.description = '''On the spreadsheet, it says that this work amends '{}' – see row {}.

The amendment could not be linked automatically.
Possible reasons:
– more than one amended work listed
– a typo in the spreadsheet
– no date for the amendment
– the amended work hasn't been imported.

Check the spreadsheet for reference and link it/them manually,
or add the 'Pending commencement' label to this task if it doesn't have a date yet.'''.format(amended_title, info['row'])

        elif task_type == 'link-repeal':
            task.title = 'Link repeal'
            task.description = '''On the spreadsheet, it says that this work was repealed by '{}' – see row {}.

The repeal could not be linked automatically.
Possible reasons:
– a typo in the spreadsheet
– no date for the repeal
– the repealing work hasn't been imported.

Check the spreadsheet for reference and link it manually,
or add the 'Pending commencement' label to this task if it doesn't have a date yet.'''.format(info['repealed_by'], info['row'])

        elif task_type == 'link-primary-work':
            task.title = 'Link primary work'
            task.description = '''On the spreadsheet, it says that this work's primary work is '{}' – see row {}.

The primary work could not be linked automatically.
Possible reasons:
– a typo in the spreadsheet
– the primary work hasn't been imported.

Check the spreadsheet for reference and link it manually.'''.format(info['primary_work'], info['row'])

        task.country = self.country
        task.locality = self.locality
        task.work = work
        task.code = task_type
        task.created_by_user = self.user

        # need to save before assigning workflow because of M2M relation
        task.save()
        if self.workflow:
            task.workflows = [self.workflow]
            task.save()

        return task

    def find_work_by_title(self, title):
        potential_matches = Work.objects.filter(title=title, country=self.country, locality=self.locality)
        if len(potential_matches) == 1:
            return potential_matches.first()

