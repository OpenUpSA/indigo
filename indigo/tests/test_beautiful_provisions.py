# -*- coding: utf-8 -*-
from copy import deepcopy
from dotmap import DotMap
from django.test import TestCase

from indigo.analysis.toc.base import TOCElement, TOCBuilderBase
from indigo_api.templatetags.indigo import CommencementsBeautifier


class BeautifulProvisionsTestCase(TestCase):
    def setUp(self):
        self.beautifier = CommencementsBeautifier(commenced=True)
        self.commenceable_provisions = [TOCElement(
            element=None, component=None, children=[], type_='section',
            id_=f'section-{number}', num=f'{number}.', basic_unit=True
        ) for number in range(1, 31)]
        self.toc_plugin = TOCBuilderBase()

        items_3 = [TOCElement(
            element=None, component=None, children=[], type_='item',
            id_=f'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_{number}',
            num=f'({number})', basic_unit=False
        ) for number in ['A', 'B']]

        items_2 = [TOCElement(
            element=None, component=None, children=[], type_='item',
            id_=f'sec_1__subsec_1__list_1__item_a__list_1__item_{number}',
            num=f'({number})', basic_unit=False
        ) for number in ['i', 'ii', 'iii']]
        items_2[1].children = items_3

        items_1 = [TOCElement(
            element=None, component=None, children=[], type_='item',
            id_=f'sec_1__subsec_1__list_1__item_{number}', num=f'({number})', basic_unit=False
        ) for number in ['a', 'aA', 'b', 'c']]
        items_1[0].children = items_2

        subsections = [TOCElement(
            element=None, component=None, children=[], type_='subsection',
            id_=f'sec_1__subsec_{number}', num=f'({number})', basic_unit=False
        ) for number in range(1, 5)]
        subsections[0].children = items_1

        sections = [TOCElement(
            element=None, component=None, children=[], type_='section',
            id_=f'sec_{number}', num=f'{number}.', basic_unit=True
        ) for number in range(1, 8)]
        sections[0].children = subsections

        parts = [TOCElement(
            element=None, component=None, children=[], type_='part',
            id_=f'chp_1__part_{number}', num=number, basic_unit=False
        ) for number in ['A', 'B']]
        parts[0].children = sections[:3]
        parts[1].children = sections[3:5]

        chapters = [TOCElement(
            element=None, component=None, children=[], type_='chapter',
            id_=f'chp_{number}', num=number, basic_unit=False
        ) for number in ['1', '2']]
        chapters[0].children = parts
        chapters[1].children = sections[5:]

        self.chapters = chapters

    def test_beautiful_provisions_basic(self):
        provision_ids = ['section-1', 'section-2', 'section-3', 'section-4']
        provisions = self.beautifier.decorate_provisions(self.commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 1–4')

        provision_ids = ['section-2', 'section-3', 'section-4', 'section-5']
        provisions = self.beautifier.decorate_provisions(self.commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 2–5')

        provision_ids = ['section-1', 'section-2', 'section-3']
        provisions = self.beautifier.decorate_provisions(self.commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 1–3')

        provision_ids = ['section-1', 'section-3', 'section-4', 'section-5', 'section-6']
        provisions = self.beautifier.decorate_provisions(self.commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 1; section 3–6')

        provision_ids = ['section-1', 'section-2', 'section-3', 'section-4', 'section-5', 'section-7']
        provisions = self.beautifier.decorate_provisions(self.commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 1–5; section 7')

        provision_ids = ['section-1', 'section-3', 'section-4', 'section-5', 'section-6', 'section-8']
        provisions = self.beautifier.decorate_provisions(self.commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 1; section 3–6; section 8')

        provision_ids = ['section-1', 'section-4', 'section-5', 'section-6', 'section-7', 'section-8', 'section-9', 'section-10', 'section-11', 'section-12', 'section-14', 'section-16', 'section-20', 'section-21']
        provisions = self.beautifier.decorate_provisions(self.commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 1; section 4–12; section 14; section 16; section 20–21')

    def test_one_item(self):
        provision_ids = ['section-23']
        provisions = self.beautifier.decorate_provisions(self.commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 23')

    def test_two_items(self):
        provision_ids = ['section-23', 'section-25']
        provisions = self.beautifier.decorate_provisions(self.commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 23; section 25')

    def test_three_items(self):
        provision_ids = ['section-23', 'section-24', 'section-25']
        provisions = self.beautifier.decorate_provisions(self.commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 23–25')

    def test_one_excluded(self):
        commenceable_provisions = [TOCElement(
            element=None, component=None, children=[], type_='section',
            id_=f'section-{number}', num=f'{number}.', basic_unit=True
        ) for number in range(1, 4)]

        provision_ids = ['section-1', 'section-2']
        provisions = self.beautifier.decorate_provisions(commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 1–2')

        provision_ids = ['section-2', 'section-3']
        provisions = self.beautifier.decorate_provisions(commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 2–3')

    def run_nested(self, provision_ids):
        nested_toc = deepcopy(self.chapters)
        provisions = self.beautifier.decorate_provisions(nested_toc, provision_ids)
        return self.beautifier.make_beautiful(provisions)

    def test_nested_full_containers(self):
        # Don't dig down further than what is fully commenced
        provision_ids = [
            'chp_1', 'chp_1__part_A', 'sec_1', 'sec_1__subsec_1',
            'sec_1__subsec_1__list_1__item_a',
            'sec_1__subsec_1__list_1__item_a__list_1__item_i',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_A',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_B',
            'sec_1__subsec_1__list_1__item_a__list_1__item_iii',
            'sec_1__subsec_1__list_1__item_aA',
            'sec_1__subsec_1__list_1__item_b',
            'sec_1__subsec_1__list_1__item_c',
            'sec_1__subsec_2', 'sec_1__subsec_3', 'sec_1__subsec_4',
            'sec_2', 'sec_3',
            'chp_1__part_B', 'sec_4', 'sec_5',
            'chp_2', 'sec_6', 'sec_7',
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1 (section 1–5); Chapter 2 (section 6–7)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1 (section 1–5); Chapter 2 (section 6–7)', self.run_nested(provision_ids))

        provision_ids = [
            'chp_1', 'chp_1__part_A',
            'sec_1', 'sec_1__subsec_1',
            'sec_1__subsec_1__list_1__item_a',
            'sec_1__subsec_1__list_1__item_a__list_1__item_i',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_A',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_B',
            'sec_1__subsec_1__list_1__item_a__list_1__item_iii',
            'sec_1__subsec_1__list_1__item_aA',
            'sec_1__subsec_1__list_1__item_b',
            'sec_1__subsec_1__list_1__item_c',
            'sec_1__subsec_2', 'sec_1__subsec_3', 'sec_1__subsec_4',
            'sec_2', 'sec_3',
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A (section 1–3)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A (section 1–3)', self.run_nested(provision_ids))

        # don't repeat 'Chapter 1' before Part B
        provision_ids = [
            'sec_2', 'sec_3',
            'chp_1__part_B', 'sec_4', 'sec_5',
            'chp_2', 'sec_6', 'sec_7'
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part A, section 2–3; Part B (section 4–5); Chapter 2 (section 6–7)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part A, section 2–3; Part B (section 4–5); Chapter 2 (section 6–7)', self.run_nested(provision_ids))

    def test_nested_partial_containers(self):
        # Chapter 1 is mentioned regardless because it's given
        provision_ids = ['chp_1', 'sec_2']
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A, section 2', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A, section 2', self.run_nested(provision_ids))

        # Chapter 1, Part B are mentioned regardless because they're given
        provision_ids = [
            'chp_1', 'chp_1__part_A',
            'sec_1', 'sec_1__subsec_1',
            'sec_1__subsec_1__list_1__item_a',
            'sec_1__subsec_1__list_1__item_a__list_1__item_i',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_A',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_B',
            'sec_1__subsec_1__list_1__item_a__list_1__item_iii',
            'sec_1__subsec_1__list_1__item_aA',
            'sec_1__subsec_1__list_1__item_b',
            'sec_1__subsec_1__list_1__item_c',
            'sec_1__subsec_2', 'sec_1__subsec_3', 'sec_1__subsec_4',
            'sec_2', 'sec_3',
            'chp_1__part_B',
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A (section 1–3); Part B (in part)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A (section 1–3); Part B (in part)', self.run_nested(provision_ids))

        provision_ids = [
            'chp_1', 'chp_1__part_A',
            'sec_1', 'sec_1__subsec_1',
            'sec_1__subsec_1__list_1__item_a',
            'sec_1__subsec_1__list_1__item_a__list_1__item_i',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_A',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_B',
            'sec_1__subsec_1__list_1__item_a__list_1__item_iii',
            'sec_1__subsec_1__list_1__item_aA',
            'sec_1__subsec_1__list_1__item_b',
            'sec_1__subsec_1__list_1__item_c',
            'sec_1__subsec_2', 'sec_1__subsec_3', 'sec_1__subsec_4',
            'sec_2', 'sec_3',
            'chp_1__part_B', 'sec_4',
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A (section 1–3); Part B (in part); Part B, section 4', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A (section 1–3); Part B (in part); Part B, section 4', self.run_nested(provision_ids))

        # Chapter 1, Part A is mentioned (even though it's not given) for context
        provision_ids = ['chp_1', 'sec_2', 'chp_1__part_B']
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A, section 2; Part B (in part)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A, section 2; Part B (in part)', self.run_nested(provision_ids))

        provision_ids = ['sec_2', 'chp_1__part_B']
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part A, section 2; Part B (in part)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part A, section 2; Part B (in part)', self.run_nested(provision_ids))

        provision_ids = [
            'chp_1__part_A',
            'sec_1', 'sec_1__subsec_1',
            'sec_1__subsec_1__list_1__item_a',
            'sec_1__subsec_1__list_1__item_a__list_1__item_i',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_A',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_B',
            'sec_1__subsec_1__list_1__item_a__list_1__item_iii',
            'sec_1__subsec_1__list_1__item_aA',
            'sec_1__subsec_1__list_1__item_b',
            'sec_1__subsec_1__list_1__item_c',
            'sec_1__subsec_2', 'sec_1__subsec_3', 'sec_1__subsec_4',
            'sec_2', 'sec_3', 'sec_4',
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part A (section 1–3); Part B, section 4', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part A (section 1–3); Part B, section 4', self.run_nested(provision_ids))

        # Part B isn't given in full even though all its basic units have commenced because it's not mentioned 
        # Both Part A and Part B are given for context 
        provision_ids = ['chp_1', 'sec_2', 'sec_4', 'sec_5']
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A, section 2; Part B, section 4–5', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A, section 2; Part B, section 4–5', self.run_nested(provision_ids))

        provision_ids = [
            'chp_1__part_A',
            'sec_1', 'sec_1__subsec_1',
            'sec_1__subsec_1__list_1__item_a',
            'sec_1__subsec_1__list_1__item_a__list_1__item_i',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_A',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_B',
            'sec_1__subsec_1__list_1__item_a__list_1__item_iii',
            'sec_1__subsec_1__list_1__item_aA',
            'sec_1__subsec_1__list_1__item_b',
            'sec_1__subsec_1__list_1__item_c',
            'sec_1__subsec_2', 'sec_1__subsec_3', 'sec_1__subsec_4',
            'sec_2', 'sec_3', 'sec_4', 'sec_5',
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part A (section 1–3); Part B, section 4–5', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part A (section 1–3); Part B, section 4–5', self.run_nested(provision_ids))

        provision_ids = ['chp_1', 'sec_2', 'chp_1__part_B', 'sec_4', 'sec_5']
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A, section 2; Part B (section 4–5)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A, section 2; Part B (section 4–5)', self.run_nested(provision_ids))

        provision_ids = ['chp_1__part_B']
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part B (in part)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part B (in part)', self.run_nested(provision_ids))

    def test_nested_basic_units(self):
        provision_ids = [
            'sec_2', 'sec_3',
            'chp_1__part_B', 'sec_5',
            'chp_2', 'sec_7'
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part A, section 2–3; Part B (in part); Part B, section 5; Chapter 2 (in part); Chapter 2, section 7', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part A, section 2–3; Part B (in part); Part B, section 5; Chapter 2 (in part); Chapter 2, section 7', self.run_nested(provision_ids))

        provision_ids = [
            'sec_2', 'sec_3',
            'sec_5',
            'sec_7'
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part A, section 2–3; Part B, section 5; Chapter 2, section 7', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part A, section 2–3; Part B, section 5; Chapter 2, section 7', self.run_nested(provision_ids))

        provision_ids = ['sec_4', 'chp_2', 'sec_6']
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part B, section 4; Chapter 2 (in part); Chapter 2, section 6', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part B, section 4; Chapter 2 (in part); Chapter 2, section 6', self.run_nested(provision_ids))

        provision_ids = ['sec_4', 'chp_2']
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part B, section 4; Chapter 2 (in part)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part B, section 4; Chapter 2 (in part)', self.run_nested(provision_ids))

    def test_nested_single_subprovisions(self):
        provision_ids = ['sec_1__subsec_3']
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part A, section 1(3)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part A, section 1(3)', self.run_nested(provision_ids))

        provision_ids = ['sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_A']
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part A, section 1(1)(a)(ii)(A)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part A, section 1(1)(a)(ii)(A)', self.run_nested(provision_ids))

    def test_nested_multiple_subprovisions(self):
        # Subprovisions are listed separately with their parent context (up to basic unit) prepended.
        # Note 1(1)(a)(ii)(A) and (B) aren't commenced. They'll be listed separatey under 'uncommenced'.
        provision_ids = [
            'sec_1__subsec_1__list_1__item_a__list_1__item_i',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii',
            'sec_1__subsec_1__list_1__item_b', 'sec_1__subsec_1__list_1__item_c'
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part A, section 1(1)(a)(i), 1(1)(a)(ii), 1(1)(b), 1(1)(c)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part A, section 1(1)(a)(i), 1(1)(a)(ii), 1(1)(b), 1(1)(c)', self.run_nested(provision_ids))

        provision_ids = [
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_A',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii__list_1__item_B',
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part A, section 1(1)(a)(ii)(A), 1(1)(a)(ii)(B)', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part A, section 1(1)(a)(ii)(A), 1(1)(a)(ii)(B)', self.run_nested(provision_ids))

        # If a basic unit isn't fully commenced, don't end up with section 1(1)(a), 1(1)(c), 1(2), 1(3)–2
        provision_ids = [
            'chp_1',
            'chp_1__part_A',
            'sec_1',
            'sec_1__subsec_1',
            'sec_1__subsec_1__list_1__item_a',
            'sec_1__subsec_1__list_1__item_a__list_1__item_i',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii',
            'sec_1__subsec_1__list_1__item_a__list_1__item_iii',
            'sec_1__subsec_1__list_1__item_c',
            'sec_1__subsec_2',
            'sec_1__subsec_3',
            'sec_3'
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A (in part); Part A, section 1(1)(a)(i), 1(1)(a)(ii), 1(1)(a)(iii), 1(1)(c), 1(2), 1(3); section 3', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A (in part); Part A, section 1(1)(a)(i), 1(1)(a)(ii), 1(1)(a)(iii), 1(1)(c), 1(2), 1(3); section 3', self.run_nested(provision_ids))

        provision_ids = [
            'chp_1',
            'chp_1__part_A',
            'sec_1',
            'sec_1__subsec_1',
            'sec_1__subsec_1__list_1__item_a',
            'sec_1__subsec_1__list_1__item_a__list_1__item_i',
            'sec_1__subsec_1__list_1__item_a__list_1__item_ii',
            'sec_1__subsec_1__list_1__item_a__list_1__item_iii',
            'sec_1__subsec_1__list_1__item_c',
            'sec_1__subsec_2',
            'sec_1__subsec_3',
            'sec_2'
        ]
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A (in part); Part A, section 1(1)(a)(i), 1(1)(a)(ii), 1(1)(a)(iii), 1(1)(c), 1(2), 1(3); section 2', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1 (in part); Chapter 1, Part A (in part); Part A, section 1(1)(a)(i), 1(1)(a)(ii), 1(1)(a)(iii), 1(1)(c), 1(2), 1(3); section 2', self.run_nested(provision_ids))

        provision_ids = ['sec_1__subsec_1__list_1__item_b', 'sec_4']
        self.beautifier.commenced = True
        self.assertEqual('Chapter 1, Part A, section 1(1)(b); Part B, section 4', self.run_nested(provision_ids))
        self.beautifier.commenced = False
        self.assertEqual('Chapter 1, Part A, section 1(1)(b); Part B, section 4', self.run_nested(provision_ids))

    def run_lonely(self, provision_ids):
        lonely_item = TOCElement(
            element=None, component=None, children=[], type_='item', id_='item_xxx', num='(xxx)', basic_unit=False
        )

        nested_toc = deepcopy(self.chapters)
        nested_toc.insert(0, lonely_item)
        provisions = self.beautifier.decorate_provisions(nested_toc, provision_ids)
        return self.beautifier.make_beautiful(provisions)

    def test_lonely_subprovisions(self):
        provision_ids = [
            'item_xxx',
        ]

        self.beautifier.commenced = True
        self.assertEqual('item (xxx)', self.run_lonely(provision_ids))

        self.beautifier.commenced = False
        self.assertEqual('item (xxx)', self.run_lonely(provision_ids))

    def test_provisions_out_of_sync(self):
        provision_ids = ['section-29', 'section-30', 'section-31', 'section-32']
        provisions = self.beautifier.decorate_provisions(self.commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, 'section 29–30')

        provision_ids = ['section-31', 'section-32', 'section-33', 'section-34']
        provisions = self.beautifier.decorate_provisions(self.commenceable_provisions, provision_ids)
        description = self.beautifier.make_beautiful(provisions)
        self.assertEqual(description, '')

    def test_inserted(self):
        pit_1_provisions = ['1', '2', '3']
        pit_2_provisions = ['1', '1A', '2', '2A', '3', '3A']
        provisions = []
        id_set = set()
        for pit in [pit_1_provisions, pit_2_provisions]:
            items = [DotMap(id=f'section-{p}') for p in pit]
            self.toc_plugin.insert_provisions(provisions, id_set, items)
        provision_ids = [p.id for p in provisions]
        self.assertEqual(provision_ids, [
            'section-1',
            'section-1A',
            'section-2',
            'section-2A',
            'section-3',
            'section-3A',
        ])

    def test_removed_basic(self):
        pit_1_provisions = ['1', '2', '3', '4', '5', '6']
        pit_2_provisions = ['1', '3', '4']
        provisions = []
        id_set = set()
        for pit in [pit_1_provisions, pit_2_provisions]:
            items = [DotMap(id=f'section-{p}') for p in pit]
            self.toc_plugin.insert_provisions(provisions, id_set, items)
        provision_ids = [p.id for p in provisions]
        self.assertEqual(provision_ids, [
            'section-1',
            'section-2',
            'section-3',
            'section-4',
            'section-5',
            'section-6',
        ])

    def test_removed_inserted(self):
        pit_1_provisions = ['1', '2', '3', '4', '5']
        pit_2_provisions = ['3', '4', '4A', '4B', '4C', '4D', '5', '5A']
        provisions = []
        id_set = set()
        for pit in [pit_1_provisions, pit_2_provisions]:
            items = [DotMap(id=f'section-{p}') for p in pit]
            self.toc_plugin.insert_provisions(provisions, id_set, items)
        provision_ids = [p.id for p in provisions]
        self.assertEqual(provision_ids, [
            'section-1',
            'section-2',
            'section-3',
            'section-4',
            'section-4A',
            'section-4B',
            'section-4C',
            'section-4D',
            'section-5',
            'section-5A',
        ])

        # provisions removed, then others inserted
        pit_1_provisions = ['1', '2', '3', '4', '5']
        pit_2_provisions = ['1', '4', '5']
        pit_3_provisions = ['1', '4', '4A', '4B', '4C', '5']
        provisions = []
        id_set = set()
        for pit in [pit_1_provisions, pit_2_provisions, pit_3_provisions]:
            items = [DotMap(id=f'section-{p}') for p in pit]
            self.toc_plugin.insert_provisions(provisions, id_set, items)
        provision_ids = [p.id for p in provisions]
        self.assertEqual(provision_ids, [
            'section-1',
            'section-2',
            'section-3',
            'section-4',
            'section-4A',
            'section-4B',
            'section-4C',
            'section-5',
        ])

        # provisions removed, others inserted at same index
        # unfortunately in this case 2A to 2C will be inserted after 3,
        # because they might as well be 4A to 4C – there's no way to know for sure
        # when a new provision is inserted at the index of a removed one.
        pit_1_provisions = ['1', '2', '3', '4', '5']
        pit_3_provisions = ['1', '2', '2A', '2B', '2C', '5']
        provisions = []
        id_set = set()
        for pit in [pit_1_provisions, pit_2_provisions, pit_3_provisions]:
            items = [DotMap(id=f'section-{p}') for p in pit]
            self.toc_plugin.insert_provisions(provisions, id_set, items)
        provision_ids = [p.id for p in provisions]
        self.assertEqual(provision_ids, [
            'section-1',
            'section-2',
            'section-3',
            'section-4',
            'section-2A',
            'section-2B',
            'section-2C',
            'section-5',
        ])

    def test_inserted_removed_edge(self):
        # new provision inserted at same index as a removed provision
        pit_1_provisions = ['1', '2', '3']
        pit_2_provisions = ['1', 'XX', '3']
        provisions = []
        id_set = set()
        for pit in [pit_1_provisions, pit_2_provisions]:
            items = [DotMap(id=f'section-{p}') for p in pit]
            self.toc_plugin.insert_provisions(provisions, id_set, items)
        provision_ids = [p.id for p in provisions]
        self.assertEqual(provision_ids, [
            'section-1',
            'section-2',
            'section-XX',
            'section-3',
        ])

        # provision inserted, removed, another inserted
        pit_1_provisions = ['1', '2', '3']
        pit_2_provisions = ['1', '2', '2A', '2B', '3']
        pit_3_provisions = ['2C', '3']
        provisions = []
        id_set = set()
        for pit in [pit_1_provisions, pit_2_provisions, pit_3_provisions]:
            items = [DotMap(id=f'section-{p}') for p in pit]
            self.toc_plugin.insert_provisions(provisions, id_set, items)
        provision_ids = [p.id for p in provisions]
        self.assertEqual(provision_ids, [
            'section-1',
            'section-2',
            'section-2A',
            'section-2B',
            'section-2C',
            'section-3',
        ])

        # absolute garbage
        # pit 2's provisions will be tacked onto the end
        pit_1_provisions = ['1', '2', '3', '4', '5', '6']
        pit_2_provisions = ['3A', '3B', 'X', 'Y', 'Z']
        pit_3_provisions = ['1', '2', '3', '4', '4A', '4B', '5', '6']
        provisions = []
        id_set = set()
        for pit in [pit_1_provisions, pit_2_provisions, pit_3_provisions]:
            items = [DotMap(id=f'section-{p}') for p in pit]
            self.toc_plugin.insert_provisions(provisions, id_set, items)
        provision_ids = [p.id for p in provisions]
        self.assertEqual(provision_ids, [
            'section-1',
            'section-2',
            'section-3',
            'section-4',
            'section-4A',
            'section-4B',
            'section-5',
            'section-6',
            'section-3A',
            'section-3B',
            'section-X',
            'section-Y',
            'section-Z',
        ])
