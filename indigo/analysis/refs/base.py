from lxml import etree
import re

from indigo.analysis.markup import TextPatternMarker, MultipleTextPatternMarker
from indigo.plugins import LocaleBasedMatcher, plugins
from indigo.xmlutils import closest
from indigo_api.models import Subtype, Work


class BaseRefsFinder(LocaleBasedMatcher, TextPatternMarker):
    """ Finds references to Acts in documents.
    """
    marker_tag = 'ref'

    def find_references_in_document(self, document):
        """ Find references in +document+, which is an Indigo Document object.
        """
        # we need to use etree, not objectify, so we can't use document.doc.root,
        # we have to re-parse it
        root = etree.fromstring(document.content)
        self.document = document
        self.frbr_uri = document.doc.frbr_uri
        self.setup(root)
        self.markup_patterns(root)
        document.content = etree.tostring(root, encoding='utf-8').decode('utf-8')

    def is_valid(self, node, match):
        if self.make_href(match) != self.frbr_uri.work_uri():
            return True

    def markup_match(self, node, match):
        """ Markup the match with a ref tag. The first group in the match is substituted with the ref.
        """
        ref = etree.Element(self.marker_tag)
        ref.text = match.group('ref')
        ref.set('href', self.make_href(match))
        return ref, match.start('ref'), match.end('ref')

    def make_href(self, match):
        """ Turn this match into a full FRBR URI href.
            Check for an existing Act with that FRBR URI in the locality first; default to national (may or may not exist).
        """
        link_uri = f"/akn/{self.frbr_uri.country}/act/{match.group('year')}/{match.group('num')}"
        if self.frbr_uri.locality:
            local = f"/akn/{self.frbr_uri.country}-{self.frbr_uri.locality}/act/{match.group('year')}/{match.group('num')}"
            if Work.objects.filter(frbr_uri=local).exists():
                link_uri = local

        return link_uri


@plugins.register('refs')
class RefsFinderENG(BaseRefsFinder):
    """ Finds references to Acts in documents, of the form:

        Act 52 of 2001
        Act no. 52 of 1998
        Income Tax Act, 1962 (No 58 of 1962)

    """

    # country, language, locality
    locale = (None, 'eng', None)

    pattern_re = re.compile(
        r'''\bAct,?\s+
            (\d{4}\s+)?
            \(?
            (?P<ref>
             ([nN]o\.?\s*)?
             (?P<num>\d+)\s+
             of\s+
             (?P<year>\d{4})
            )
        ''', re.X)
    candidate_xpath = ".//text()[contains(., 'Act') and not(ancestor::a:ref)]"


@plugins.register('refs-subtypes')
class RefsFinderSubtypesENG(BaseRefsFinder):
    """ Finds references to works other than Acts in documents, of the form:

        P 52 of 2001
        Ordinance no. 52 of 1998
        GN 1/2009
        General Notice 12 published in Gazette 12345 of 2019

    """

    # country, language, locality
    locale = (None, 'eng', None)

    def setup(self, root):
        self.setup_subtypes()
        self.setup_candidate_xpath()
        self.setup_pattern_re()
        # If we don't have subtypes, don't let the superclass do setup, because it will fail.
        # We're going to opt-out of doing any work anyway.
        if self.subtypes:
            super().setup(root)

    def setup_subtypes(self):
        self.full_subtypes = Subtype.objects.all()
        self.subtypes = [s.name for s in self.full_subtypes] + \
                        [s.abbreviation for s in self.full_subtypes]

    def setup_candidate_xpath(self):
        xpath_contains = " or ".join(
            [f"contains(translate(., '{s.upper()}', '{s.lower()}'), "
             f"'{s.lower()}')"
             for s in self.subtypes])
        self.candidate_xpath = f".//text()[({xpath_contains}) and not(ancestor::a:ref)]"

    def setup_pattern_re(self):
        subtypes_for_re = '|'.join([re.escape(s) for s in self.subtypes])
        self.pattern_re = re.compile(
            fr'''
                (?P<ref>
                    (?P<subtype>{subtypes_for_re})\s*
                    (No\.?\s*)?
                    (?P<num>\d+)
                    .{{0,60}}(\s|/)
                    (?P<year>\d{{4}})\b
                )
            ''', re.X | re.I)

    def markup_patterns(self, root):
        # don't do anything if there are no subtypes
        if self.subtypes:
            super().markup_patterns(root)

    def make_href(self, match):
        # use correct subtype for FRBR URI
        subtype = match.group('subtype').lower()
        subtype_for_uri = None
        for s in self.full_subtypes:
            if subtype == s.name.lower() or subtype == s.abbreviation.lower():
                subtype_for_uri = s.abbreviation
                break

        place = f'{self.frbr_uri.country}'
        if self.frbr_uri.locality:
            place = f'{self.frbr_uri.country}-{self.frbr_uri.locality}'

        if subtype_for_uri:
            return f'/akn/{place}/act/{subtype_for_uri}/{match.group("year")}/{match.group("num")}'


@plugins.register('refs-cap')
class RefsFinderCapENG(BaseRefsFinder):
    """ Finds references to works with cap numbers, of the form:

        Cap. 231
        Cap A4

    """
    # country, language, locality
    locale = (None, 'eng', None)

    pattern_re = re.compile(
        r'''
            (?P<ref>
             \bCap\.?\s*
             (?P<num>\w+)
            )
        ''', re.X)
    candidate_xpath = ".//text()[contains(., 'Cap') and not(ancestor::a:ref)]"

    def setup(self, root):
        self.setup_cap_numbers(self.document)
        super().setup(root)

    def setup_cap_numbers(self, document):
        country = document.work.country
        locality = document.work.locality
        place = locality or country
        cap_strings = [p for p in place.settings.work_properties if p.startswith('cap')]

        self.cap_numbers = {w.properties[c]: w.frbr_uri for c in cap_strings for w in Work.objects.filter(country=country, locality=locality) if w.properties.get(c)}

    def is_valid(self, node, match):
        return self.cap_numbers.get(match.group('num'))

    def make_href(self, match):
        return self.cap_numbers[match.group('num')]


class BaseInternalRefsFinder(LocaleBasedMatcher, MultipleTextPatternMarker):
    """ Finds internal references in documents, such as to sections.

    The item_re and pattern_re patterns must both have a named capture group
    called 'ref', which is the full reference to me marked up.
    """
    marker_tag = 'ref'

    # the ancestor elements that can contain references
    ancestors = ['body', 'mainBody', 'conclusions']

    def find_references_in_document(self, document):
        """ Find references in +document+, which is an Indigo Document object.
        """
        # we need to use etree, not objectify, so we can't use document.doc.root,
        # we have to re-parse it
        root = etree.fromstring(document.content)
        self.setup(root)
        self.markup_patterns(root)
        document.content = etree.tostring(root, encoding='utf-8').decode('utf-8')

    def is_valid(self, node, match):
        return self.find_target(node, match) is not None

    def is_item_valid(self, node, match):
        return self.is_valid(node, match)

    def markup_match(self, node, match):
        ref = etree.Element(self.marker_tag)
        ref.text = match.group('ref')
        ref.set('href', self.make_href(node, match))
        return ref, match.start('ref'), match.end('ref')

    def find_target(self, node, match):
        """ Return the target element that this reference targets.
        """
        raise NotImplementedError()

    def make_href(self, node, match):
        """ Return the target href for this match.
        """
        target = self.find_target(node, match)
        return '#' + target.get('eId')


@plugins.register('internal-refs')
class SectionRefsFinderENG(BaseInternalRefsFinder):
    """ Finds internal references to sections in documents, of the form:

        # singletons
        section 26
        section 26B

        # lists
        sections 22 and 32
        and sections 19, 22 and 23, unless it appears to him
        and sections 19, 22, and 23 (oxford comma)
        and sections 19,22 and 23 (incorrect spacing)
        Sections 24, 26, 28, 36, 42(2), 46, 48, 49(2), 52, 53, 54 and 56 shall mutatis mutandis
        sections 23, 24, 25, 26 and 28;
        sections 22(1) and 25(3)(b);
        sections 18, 61 and 62(1).
        in terms of section 2 or 7
        A person who contravenes sections 4(1) and (2), 6(3), 10(1) and (2), 11(1), 12(1), 19(1), 19(3), 20(1), 20(2), 21(1), 22(1), 24(1), 25(3), (4) , (5) and (6) , 26(1), (2), (3) and (5), 28(1), (2) and (3) is guilty of an offence.

        TODO: match subsections
        TODO: match paragraphs
        TODO: match ranges of sections
    """

    # country, language, locality
    locale = (None, 'eng', None)

    pattern_re = re.compile(
        r'''\b
        (
          (?P<ref>
            (?<!-)sections?\s+
            (?P<num>\d+[A-Z0-9]*)    # first section number, including subsections
          )
          (
            (\s*(,|and|or))*         # list separators
            (\s*\([A-Z0-9]+\))+      # bracketed subsections of first number
          )*
          (\s*                       # optional list of sections
            (\s*(,|and|or))*         # list separators
            (
              \s*\d+[A-Z0-9]*(
                (\s*(,|and|or))*     # list separators
                (\s*\([A-Z0-9]+\))+
              )*
            )
          )*
        )
        (\s+of\s+(this)?|\s+thereof)?
        ''',
        re.X | re.IGNORECASE)

    # individual numbers in the list grouping above
    # we use <ref> and <num> named captures so that the is_valid and make_ref
    # methods can handle matches from both ref_re and this re.
    # negative lookaround for parentheses around each number in the run guards against subsections being picked up as section numbers, e.g.
    # sections 4(1) and (2), 25(3), (4), (5) and (6), etc
    item_re = re.compile(r'(?P<ref>(?P<num>(?<!\()\d+[A-Z0-9]*(?!\))))(\s*\([A-Z0-9]+\))*', re.IGNORECASE)

    candidate_xpath = ".//text()[contains(translate(., 'S', 's'), 'section') and not(ancestor::a:ref)]"
    match_cache = {}

    def setup(self, root):
        super().setup(root)
        self.ancestor_tags = set(f'{{{self.ns}}}{t}' for t in self.ancestors)

    def is_valid(self, node, match):
        # check that it's not an external reference
        ref = match.group(0)
        if ref.endswith('of ') or ref.endswith('thereof'):
            return False
        return True

    def is_item_valid(self, node, match):
        return self.find_target(node, match) is not None

    def find_target(self, node, match):
        num = match.group('num')
        # find the closest ancestor to scope the lookups to
        ancestor = closest(node, lambda e: e.tag in self.ancestor_tags)
        candidate_elements = ancestor.xpath(f".//a:section[a:num[text()='{num}.']]", namespaces=self.nsmap)
        if candidate_elements:
            self.match_cache[num] = candidate_elements[0]
            return candidate_elements[0]

    def make_href(self, node, match):
        target = self.match_cache[match.group('num')]
        return '#' + target.get('eId')
