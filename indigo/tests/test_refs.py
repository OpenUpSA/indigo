# -*- coding: utf-8 -*-
from lxml import etree

from django.conf import settings
from django.test import TestCase

from cobalt import FrbrUri

from indigo.analysis.refs.base import SectionRefsFinderENG, RefsFinderENG, RefsFinderSubtypesENG, RefsFinderCapENG

from indigo_api.models import Document, Language, Work, Country, User, Subtype
from indigo_api.tests.fixtures import document_fixture


class SectionRefsFinderTestCase(TestCase):
    fixtures = ['languages_data', 'countries']

    def setUp(self):
        self.work = Work(frbr_uri='/akn/za/act/1991/1')
        self.section_refs_finder = SectionRefsFinderENG()
        self.eng = Language.for_code('eng')
        self.maxDiff = None

    def test_section_basic(self):
        document = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
      <section eId="sec_7">
        <num>7.</num>
        <heading>Active ref heading</heading>
        <content>
          <p>As given in section 26, blah.</p>
          <p>As given in section 26(b), blah.</p>
          <p>As given in section 26(1)(b)(iii), blah.</p>
          <p>As given in section 26(1)(b)(iii)(bb), blah.</p>
          <p>As given in section 26(1)(b)(iii)(dd)(A), blah.</p>
          <p>As given in section 26B, blah.</p>
          <p>As given in section 26 and section 31, blah.</p>
          <p>As <i>given</i> in (we're now in a tail) section 26, blah.</p>
        </content>
      </section>
      <section eId="sec_26">
        <num>26.</num>
        <heading>Important heading</heading>
        <content>
          <p>An important provision.</p>
        </content>
      </section>
      <section eId="sec_26B">
        <num>26B.</num>
        <heading>Another important heading</heading>
        <content>
          <p>Another important provision.</p>
        </content>
      </section>
      <section eId="sec_31">
        <num>31.</num>
        <heading>More important</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
        """
            ),
            language=self.eng)

        expected = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
      <section eId="sec_7">
        <num>7.</num>
        <heading>Active ref heading</heading>
        <content>
          <p>As given in <ref href="#sec_26">section 26</ref>, blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref>(b), blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref>(1)(b)(iii), blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref>(1)(b)(iii)(bb), blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref>(1)(b)(iii)(dd)(A), blah.</p>
          <p>As given in <ref href="#sec_26B">section 26B</ref>, blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref> and <ref href="#sec_31">section 31</ref>, blah.</p>
          <p>As <i>given</i> in (we're now in a tail) <ref href="#sec_26">section 26</ref>, blah.</p>
        </content>
      </section>
      <section eId="sec_26">
        <num>26.</num>
        <heading>Important heading</heading>
        <content>
          <p>An important provision.</p>
        </content>
      </section>
      <section eId="sec_26B">
        <num>26B.</num>
        <heading>Another important heading</heading>
        <content>
          <p>Another important provision.</p>
        </content>
      </section>
      <section eId="sec_31">
        <num>31.</num>
        <heading>More important</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
        """
            ),
            language=self.eng)

        self.section_refs_finder.find_references_in_document(document)
        root = etree.fromstring(expected.content)
        expected.content = etree.tostring(root, encoding='utf-8').decode('utf-8')
        self.assertEqual(expected.content, document.content)

    def test_section_of_this(self):
        document = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
      <section eId="sec_7">
        <num>7.</num>
        <heading>Active ref heading</heading>
        <content>
          <p>As given in section 26 of this Act, blah.</p>
          <p>As given in section 26 (1) of this Act, blah.</p>
          <p>As given in section 26 (1) of this Proclamation, blah.</p>
          <p>As given in section 26(1)(b)(iii)(dd)(A) of this Act, blah.</p>
          <p>In section 26 of Act 5 of 2012 it says one thing and in section 26 of this Act it says another.</p>
          <p>As <i>given</i> in (we're now in a tail) section 26 of this Act, blah.</p>
        </content>
      </section>
      <section eId="sec_26">
        <num>26.</num>
        <heading>Important heading</heading>
        <content>
          <p>An important provision.</p>
        </content>
      </section>
        """
            ),
            language=self.eng)

        expected = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
      <section eId="sec_7">
        <num>7.</num>
        <heading>Active ref heading</heading>
        <content>
          <p>As given in <ref href="#sec_26">section 26</ref> of this Act, blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref> (1) of this Act, blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref> (1) of this Proclamation, blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref>(1)(b)(iii)(dd)(A) of this Act, blah.</p>
          <p>In section 26 of Act 5 of 2012 it says one thing and in <ref href="#sec_26">section 26</ref> of this Act it says another.</p>
          <p>As <i>given</i> in (we're now in a tail) <ref href="#sec_26">section 26</ref> of this Act, blah.</p>
        </content>
      </section>
      <section eId="sec_26">
        <num>26.</num>
        <heading>Important heading</heading>
        <content>
          <p>An important provision.</p>
        </content>
      </section>
        """
            ),
            language=self.eng)

        self.section_refs_finder.find_references_in_document(document)
        root = etree.fromstring(expected.content)
        expected.content = etree.tostring(root, encoding='utf-8').decode('utf-8')
        self.assertEqual(expected.content, document.content)

    def test_section_multiple(self):
        document = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
      <section eId="sec_7">
        <num>7.</num>
        <heading>Active ref heading</heading>
        <content>
          <p>As given in sections 26 and 31, blah.</p>
          <p>As given in sections 26, 26B, 30 and 31, blah.</p>
          <p>As given in section 26 or 31, blah.</p>
          <p>As given in sections 26 or 31, blah.</p>
          <p>As given in sections 26, 30(1) and 31, blah.</p>
          <p>As given in sections 26, 30 (1) and 31, blah.</p>
          <p>As given in sections 26(b), 30(1) or 31, blah.</p>
          <p>As given in section 26 (b), 30 (1) or 31, blah.</p>
          <p>As <i>given</i> in (we're now in a tail) section 26, 30 and 31.</p>
          <p>under sections 26,30 or 31 of this Act, blah.</p>
          <p>As given in sections 26, 30, and 31 of this Act, blah.</p>
        </content>
      </section>
      <section eId="sec_26">
        <num>26.</num>
        <heading>Important heading</heading>
        <content>
          <p>An important provision.</p>
        </content>
      </section>
      <section eId="sec_26B">
        <num>26B.</num>
        <heading>Another important heading</heading>
        <content>
          <p>Another important provision.</p>
        </content>
      </section>
      <section eId="sec_30">
        <num>30.</num>
        <heading>Less important</heading>
        <content>
          <p>Meh.</p>
        </content>
      </section>
      <section eId="sec_31">
        <num>31.</num>
        <heading>More important</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
        """
            ),
            language=self.eng)

        expected = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
      <section eId="sec_7">
        <num>7.</num>
        <heading>Active ref heading</heading>
        <content>
          <p>As given in sections <ref href="#sec_26">26</ref> and <ref href="#sec_31">31</ref>, blah.</p>
          <p>As given in sections <ref href="#sec_26">26</ref>, <ref href="#sec_26B">26B</ref>, <ref href="#sec_30">30</ref> and <ref href="#sec_31">31</ref>, blah.</p>
          <p>As given in section <ref href="#sec_26">26</ref> or <ref href="#sec_31">31</ref>, blah.</p>
          <p>As given in sections <ref href="#sec_26">26</ref> or <ref href="#sec_31">31</ref>, blah.</p>
          <p>As given in sections <ref href="#sec_26">26</ref>, <ref href="#sec_30">30</ref>(1) and <ref href="#sec_31">31</ref>, blah.</p>
          <p>As given in sections <ref href="#sec_26">26</ref>, <ref href="#sec_30">30</ref> (1) and <ref href="#sec_31">31</ref>, blah.</p>
          <p>As given in sections <ref href="#sec_26">26</ref>(b), <ref href="#sec_30">30</ref>(1) or <ref href="#sec_31">31</ref>, blah.</p>
          <p>As given in section <ref href="#sec_26">26</ref> (b), <ref href="#sec_30">30</ref> (1) or <ref href="#sec_31">31</ref>, blah.</p>
          <p>As <i>given</i> in (we're now in a tail) section <ref href="#sec_26">26</ref>, <ref href="#sec_30">30</ref> and <ref href="#sec_31">31</ref>.</p>
          <p>under sections <ref href="#sec_26">26</ref>,<ref href="#sec_30">30</ref> or <ref href="#sec_31">31</ref> of this Act, blah.</p>
          <p>As given in sections <ref href="#sec_26">26</ref>, <ref href="#sec_30">30</ref>, and <ref href="#sec_31">31</ref> of this Act, blah.</p>
        </content>
      </section>
      <section eId="sec_26">
        <num>26.</num>
        <heading>Important heading</heading>
        <content>
          <p>An important provision.</p>
        </content>
      </section>
      <section eId="sec_26B">
        <num>26B.</num>
        <heading>Another important heading</heading>
        <content>
          <p>Another important provision.</p>
        </content>
      </section>
      <section eId="sec_30">
        <num>30.</num>
        <heading>Less important</heading>
        <content>
          <p>Meh.</p>
        </content>
      </section>
      <section eId="sec_31">
        <num>31.</num>
        <heading>More important</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
        """
            ),
            language=self.eng)

        self.section_refs_finder.find_references_in_document(document)
        root = etree.fromstring(expected.content)
        expected.content = etree.tostring(root, encoding='utf-8').decode('utf-8')
        self.assertEqual(expected.content, document.content)

    def test_section_invalid(self):
        document = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
      <section eId="sec_7">
        <num>7.</num>
        <heading>Active ref heading</heading>
        <content>
          <p>As given in section 25, which isn't in this document, blah.</p>
          <p>In section 200 it says one thing and in section 26 of Act 5 of 2012 it says another.</p>
          <p>As given in section 26(1)(a) of Proclamation 9 of 1926, blah.</p>
          <p>As per Proclamation 9 of 1926, as given in section 26 thereof, blah.</p>
          <p>As per Proclamation 9 of 1926, as given in section 26 of that Proclamation, blah.</p>
          <p>As per Act 9 of 2005, as given in section 26 of that Act, blah.</p>
          <p>As given in section 26(1)(b)(iii)(dd)(A) of Act 5 of 2002, blah.</p>
          <p>As given in section 26 of Act 5 of 2012, blah.</p>
          <p>As given in section 26 of the Nursing Act, blah.</p>
          <p>As given in section 26(b) of the Nursing Act, blah.</p>
          <p>As given in section 26(b)(iii) of the Nursing Act, blah.</p>
          <p>As given in section 26 (b) (iii) of the Nursing Act, blah.</p>
          <p>As given in section 26(b)(iii)(bb) of the Nursing Act, blah.</p>
          <p>As given in section 26(b)(iii)(aa)(A) of the Nursing Act, blah.</p>
          <p>As given in section 26, 27 or 28(b) of the Nursing Act, blah.</p>
          <p>As given in section 26 or 27 of the Nursing Act, blah.</p>
          <p>As given in section 26(b)(iii)(1) of the Nursing Act, blah.</p>
          <p>As <i>given</i> in (we're now in a tail) section 26 of Act 5 of 2012, blah.</p>
          <p>As <i>given</i> in (we're now in a tail) section 26 of the Nursing Act, blah.</p>
          <p>As <i>given</i> in (we're now in a tail) sections 26, 27 and 28 of the Nursing Act, blah.</p>
          <p>As given in section 26 of Cap. C38, blah.</p>
          <p>As given in section 26 of the Criminal Code, blah.</p>
          <p>As given in sub-section 1, blah.</p>
        </content>
      </section>
      <section eId="sec_26">
        <num>26.</num>
        <heading>Important heading</heading>
        <content>
          <p>An important provision.</p>
        </content>
      </section>
        """
            ),
            language=self.eng)

        expected_content = document.content
        self.section_refs_finder.find_references_in_document(document)
        root = etree.fromstring(expected_content)
        expected_content = etree.tostring(root, encoding='utf-8').decode('utf-8')
        self.assertEqual(expected_content, document.content)

    def test_section_valid_and_invalid(self):
        document = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
      <section eId="sec_7">
        <num>7.</num>
        <heading>Active ref heading</heading>
        <content>
          <p>As given in sections 26 and 35, one of which isn't in this document, blah.</p>
          <p>As given in sections 35 and 26, one of which isn't in this document, blah.</p>
          <p>In section 200 it says one thing and in section 26 it says another.</p>
          <p>As <i>given</i> in (we're now in a tail) section 200, blah, but section 26 says something else.</p>
          <p>As <i>given</i> in (we're now in a tail) section 26 of Act 5 of 2012, blah, but section 26 of this Act says something else.</p>
        </content>
      </section>
      <section eId="sec_26">
        <num>26.</num>
        <heading>The section we want</heading>
        <content>
          <p>The provision you're looking for.</p>
        </content>
      </section>
        """
            ),
            language=self.eng)

        expected = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
      <section eId="sec_7">
        <num>7.</num>
        <heading>Active ref heading</heading>
        <content>
          <p>As given in sections <ref href="#sec_26">26</ref> and 35, one of which isn't in this document, blah.</p>
          <p>As given in sections 35 and <ref href="#sec_26">26</ref>, one of which isn't in this document, blah.</p>
          <p>In section 200 it says one thing and in <ref href="#sec_26">section 26</ref> it says another.</p>
          <p>As <i>given</i> in (we're now in a tail) section 200, blah, but <ref href="#sec_26">section 26</ref> says something else.</p>
          <p>As <i>given</i> in (we're now in a tail) section 26 of Act 5 of 2012, blah, but <ref href="#sec_26">section 26</ref> of this Act says something else.</p>
        </content>
      </section>
      <section eId="sec_26">
        <num>26.</num>
        <heading>The section we want</heading>
        <content>
          <p>The provision you're looking for.</p>
        </content>
      </section>
        """
            ),
            language=self.eng)

        self.section_refs_finder.find_references_in_document(document)
        root = etree.fromstring(expected.content)
        expected_content = etree.tostring(root, encoding='utf-8').decode('utf-8')
        self.assertEqual(expected_content, document.content)

    def test_section_edge(self):
        document = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
      <section eId="sec_1">
        <num>1.</num>
        <heading>Unimportant heading</heading>
        <content>
          <p>An unimportant provision.</p>
        </content>
      </section>
      <section eId="sec_2">
        <num>2.</num>
        <heading>Unimportant heading</heading>
        <content>
          <p>An unimportant provision.</p>
        </content>
      </section>
      <section eId="sec_3">
        <num>3.</num>
        <heading>Unimportant heading</heading>
        <content>
          <p>An unimportant provision.</p>
        </content>
      </section>
      <section eId="sec_4">
        <num>4.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_5">
        <num>5.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_6">
        <num>6.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_7">
        <num>7.</num>
        <heading>Active ref heading</heading>
        <content>
          <p>As given in section 26(1), blah.</p>
          <p>As given in section 26 (1), blah.</p>
          <p>As given in section 26(1), (2) and (3), blah.</p>
          <p>As given in section 26 (1), (2) and (3), blah.</p>
          <p>As given in sections 26(1), (2) and (3), blah.</p>
          <p>As given in sections 26 (1), (2) and (3), blah.</p>
          <p>As given in section 26 (2) and (3), blah.</p>
          <p>As given in section 26(2) and (3), blah.</p>
          <p>As given in sections 26 (2) and (3), blah.</p>
          <p>As given in sections 26(2) and (3), blah.</p>
          <p>A person who contravenes sections 4(1), (2) and (3), 6(3) and 10(1) and (2) is guilty of an offence.</p>
          <p>Subject to sections 1(4) and (5) and 4(6), no person is guilty of an offence.</p>
          <p>A person who contravenes sections 4(1) and (2), 6(3), 10(1) and (2), 11(1), 12(1), 19(1), 19(3), 20(1), 20(2), 21(1), 22(1), 24(1), 25(3), (4) , (5) and (6) , 26(1), (2), (3) and (5), 28(1), (2) and (3) is guilty of an offence.</p>
        </content>
      </section>
      <section eId="sec_10">
        <num>10.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_11">
        <num>11.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_12">
        <num>12.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_19">
        <num>19.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_20">
        <num>20.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_21">
        <num>21.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_22">
        <num>22.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_24">
        <num>24.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_25">
        <num>25.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_26">
        <num>26.</num>
        <heading>Important heading</heading>
        <content>
          <p>An important provision.</p>
        </content>
      </section>
      <section eId="sec_28">
        <num>28.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_30">
        <num>30.</num>
        <heading>Less important</heading>
        <content>
          <p>Meh.</p>
        </content>
      </section>
      <section eId="sec_31">
        <num>31.</num>
        <heading>More important</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
        """
            ),
            language=self.eng)

        expected = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
      <section eId="sec_1">
        <num>1.</num>
        <heading>Unimportant heading</heading>
        <content>
          <p>An unimportant provision.</p>
        </content>
      </section>
      <section eId="sec_2">
        <num>2.</num>
        <heading>Unimportant heading</heading>
        <content>
          <p>An unimportant provision.</p>
        </content>
      </section>
      <section eId="sec_3">
        <num>3.</num>
        <heading>Unimportant heading</heading>
        <content>
          <p>An unimportant provision.</p>
        </content>
      </section>
      <section eId="sec_4">
        <num>4.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_5">
        <num>5.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_6">
        <num>6.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_7">
        <num>7.</num>
        <heading>Active ref heading</heading>
        <content>
          <p>As given in <ref href="#sec_26">section 26</ref>(1), blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref> (1), blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref>(1), (2) and (3), blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref> (1), (2) and (3), blah.</p>
          <p>As given in <ref href="#sec_26">sections 26</ref>(1), (2) and (3), blah.</p>
          <p>As given in <ref href="#sec_26">sections 26</ref> (1), (2) and (3), blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref> (2) and (3), blah.</p>
          <p>As given in <ref href="#sec_26">section 26</ref>(2) and (3), blah.</p>
          <p>As given in <ref href="#sec_26">sections 26</ref> (2) and (3), blah.</p>
          <p>As given in <ref href="#sec_26">sections 26</ref>(2) and (3), blah.</p>
          <p>A person who contravenes sections <ref href="#sec_4">4</ref>(1), (2) and (3), <ref href="#sec_6">6</ref>(3) and <ref href="#sec_10">10</ref>(1) and (2) is guilty of an offence.</p>
          <p>Subject to sections <ref href="#sec_1">1</ref>(4) and (5) and <ref href="#sec_4">4</ref>(6), no person is guilty of an offence.</p>
          <p>A person who contravenes sections <ref href="#sec_4">4</ref>(1) and (2), <ref href="#sec_6">6</ref>(3), <ref href="#sec_10">10</ref>(1) and (2), <ref href="#sec_11">11</ref>(1), <ref href="#sec_12">12</ref>(1), <ref href="#sec_19">19</ref>(1), <ref href="#sec_19">19</ref>(3), <ref href="#sec_20">20</ref>(1), <ref href="#sec_20">20</ref>(2), <ref href="#sec_21">21</ref>(1), <ref href="#sec_22">22</ref>(1), <ref href="#sec_24">24</ref>(1), <ref href="#sec_25">25</ref>(3), (4) , (5) and (6) , <ref href="#sec_26">26</ref>(1), (2), (3) and (5), <ref href="#sec_28">28</ref>(1), (2) and (3) is guilty of an offence.</p>
        </content>
      </section>
      <section eId="sec_10">
        <num>10.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_11">
        <num>11.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_12">
        <num>12.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_19">
        <num>19.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_20">
        <num>20.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_21">
        <num>21.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_22">
        <num>22.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_24">
        <num>24.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_25">
        <num>25.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_26">
        <num>26.</num>
        <heading>Important heading</heading>
        <content>
          <p>An important provision.</p>
        </content>
      </section>
      <section eId="sec_28">
        <num>28.</num>
        <heading>Unimportant</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
      <section eId="sec_30">
        <num>30.</num>
        <heading>Less important</heading>
        <content>
          <p>Meh.</p>
        </content>
      </section>
      <section eId="sec_31">
        <num>31.</num>
        <heading>More important</heading>
        <content>
          <p>Hi!</p>
        </content>
      </section>
        """
            ),
            language=self.eng)

        self.section_refs_finder.find_references_in_document(document)
        root = etree.fromstring(expected.content)
        expected.content = etree.tostring(root, encoding='utf-8').decode('utf-8')
        self.assertEqual(expected.content, document.content)


class RefsFinderENGTestCase(TestCase):
    fixtures = ['languages_data', 'countries']

    def setUp(self):
        self.work = Work(frbr_uri='/akn/za/act/1991/1')
        self.finder = RefsFinderENG()
        self.eng = Language.for_code('eng')
        self.maxDiff = None

    def test_find_simple(self):
        document = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
        <section eId="sec_1">
          <num>1.</num>
          <heading>Tester</heading>
          <paragraph eId="sec_1.paragraph-0">
            <content>
              <p>Something to do with Act no 22 of 2012.</p>
              <p>And another thing about Act 4 of 1998.</p>
            </content>
          </paragraph>
        </section>"""
            ),
            language=self.eng)

        expected = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
        <section eId="sec_1">
          <num>1.</num>
          <heading>Tester</heading>
          <paragraph eId="sec_1.paragraph-0">
            <content>
              <p>Something to do with Act <ref href="/akn/za/act/2012/22">no 22 of 2012</ref>.</p>
              <p>And another thing about Act <ref href="/akn/za/act/1998/4">4 of 1998</ref>.</p>
            </content>
          </paragraph>
        </section>"""
            ),
            language=self.eng)

        self.finder.find_references_in_document(document)
        root = etree.fromstring(expected.content)
        expected.content = etree.tostring(root, encoding='utf-8').decode('utf-8')
        self.assertEqual(expected.content, document.content)

    def test_dont_find_self(self):
        document = Document(
            work=self.work,
            frbr_uri=self.work.frbr_uri,
            document_xml=document_fixture(
                xml="""
        <section eId="sec_1">
          <num>1.</num>
          <heading>Tester</heading>
          <paragraph eId="sec_1.paragraph-0">
            <content>
              <p>Something to do with Act 1 of 1991.</p>
              <p>Something to do with Act no 22 of 2012.</p>
              <p>And another thing about Act 4 of 1998.</p>
            </content>
          </paragraph>
        </section>"""
            ),
            language=self.eng)

        expected = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
        <section eId="sec_1">
          <num>1.</num>
          <heading>Tester</heading>
          <paragraph eId="sec_1.paragraph-0">
            <content>
              <p>Something to do with Act 1 of 1991.</p>
              <p>Something to do with Act <ref href="/akn/za/act/2012/22">no 22 of 2012</ref>.</p>
              <p>And another thing about Act <ref href="/akn/za/act/1998/4">4 of 1998</ref>.</p>
            </content>
          </paragraph>
        </section>"""
            ),
            language=self.eng)

        document.doc.frbr_uri = FrbrUri.parse(self.work.frbr_uri)
        self.finder.find_references_in_document(document)
        root = etree.fromstring(expected.content)
        expected.content = etree.tostring(root, encoding='utf-8').decode('utf-8')
        self.assertEqual(expected.content, document.content)


class RefsFinderSubtypesENGTestCase(TestCase):
    fixtures = ['languages_data', 'countries', 'subtype']

    def setUp(self):
        self.work = Work(frbr_uri='/akn/za/act/1991/1')
        self.finder = RefsFinderSubtypesENG()
        self.eng = Language.for_code('eng')
        self.maxDiff = None

    def test_find_simple(self):
        document = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
        <section eId="sec_1">
          <num>1.</num>
          <heading>Tester</heading>
          <paragraph eId="sec_1.paragraph-0">
            <content>
              <p>Something to do with GN no 102 of 2012.</p>
              <p>Something to do with Government Notice 102 of 2012.</p>
              <p>Something to do with GN 102/2012.</p>
              <p>And another thing about SI 4 of 1998.</p>
            </content>
          </paragraph>
        </section>"""
            ),
            language=self.eng)

        expected = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
        <section eId="sec_1">
          <num>1.</num>
          <heading>Tester</heading>
          <paragraph eId="sec_1.paragraph-0">
            <content>
              <p>Something to do with <ref href="/akn/za/act/gn/2012/102">GN no 102 of 2012</ref>.</p>
              <p>Something to do with <ref href="/akn/za/act/gn/2012/102">Government Notice 102 of 2012</ref>.</p>
              <p>Something to do with <ref href="/akn/za/act/gn/2012/102">GN 102/2012</ref>.</p>
              <p>And another thing about <ref href="/akn/za/act/si/1998/4">SI 4 of 1998</ref>.</p>
            </content>
          </paragraph>
        </section>"""
            ),
            language=self.eng)

        self.finder.find_references_in_document(document)
        self.assertEqual(
            etree.tostring(etree.fromstring(expected.content), encoding='utf-8').decode('utf-8'),
            document.content)

    def test_find_longer(self):
        document = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
        <section eId="sec_1">
          <num>1.</num>
          <heading>Tester</heading>
          <paragraph eId="sec_1.paragraph-0">
            <content>
              <p>Something to do with GN no 102 published on 5 March 2012.</p>
              <p>And another thing about SI 4, published in Government Gazette 12345 of 31 January 1998.</p>
            </content>
          </paragraph>
        </section>"""
            ),
            language=self.eng)

        expected = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
        <section eId="sec_1">
          <num>1.</num>
          <heading>Tester</heading>
          <paragraph eId="sec_1.paragraph-0">
            <content>
              <p>Something to do with <ref href="/akn/za/act/gn/2012/102">GN no 102 published on 5 March 2012</ref>.</p>
              <p>And another thing about <ref href="/akn/za/act/si/1998/4">SI 4, published in Government Gazette 12345 of 31 January 1998</ref>.</p>
            </content>
          </paragraph>
        </section>"""
            ),
            language=self.eng)

        self.finder.find_references_in_document(document)
        self.assertEqual(
            etree.tostring(etree.fromstring(expected.content), encoding='utf-8').decode('utf-8'),
            document.content)

    def test_no_year(self):
        document = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
        <section eId="sec_1">
          <num>1.</num>
          <heading>Tester</heading>
          <paragraph eId="sec_1.paragraph-0">
            <content>
              <p>Something to do with GN no 102 published on 5 March.</p>
              <p>And another thing about SI 4, published in Government Gazette 
12345 of 31 January.</p>
            </content>
          </paragraph>
        </section>"""
            ),
            language=self.eng)

        expected = Document(
            work=self.work,
            document_xml=document_fixture(
                xml="""
        <section eId="sec_1">
          <num>1.</num>
          <heading>Tester</heading>
          <paragraph eId="sec_1.paragraph-0">
            <content>
              <p>Something to do with GN no 102 published on 5 March.</p>
              <p>And another thing about SI 4, published in Government Gazette 
12345 of 31 January.</p>
            </content>
          </paragraph>
        </section>"""
            ),
            language=self.eng)

        self.finder.find_references_in_document(document)
        self.assertEqual(
            etree.tostring(etree.fromstring(expected.content), encoding='utf-8').decode('utf-8'),
            document.content)


class RefsFinderCapENGTestCase(TestCase):
    fixtures = ['languages_data', 'countries', 'user']

    def setUp(self):
        self.finder = RefsFinderCapENG()
        self.eng = Language.for_code('eng')
        self.maxDiff = None

    def test_find_simple(self):
        za = Country.objects.get(pk=1)
        user1 = User.objects.get(pk=1)
        settings.INDIGO['WORK_PROPERTIES'] = {
            'za': {
                'cap': 'Chapter (cap)',
            }
        }

        work = Work(
            frbr_uri='/akn/za/act/2002/5',
            title='Act 5 of 2002',
            country=za,
            created_by_user=user1,
        )
        work.properties['cap'] = '12'
        work.updated_by_user = user1
        work.save()

        document = Document(
            document_xml=document_fixture(
                xml="""
        <section eId="sec_1">
          <num>1.</num>
          <heading>Tester</heading>
          <paragraph eId="sec_1.paragraph-0">
            <content>
              <p>Something to do with Cap. 12.</p>
            </content>
          </paragraph>
        </section>"""
            ),
            language=self.eng,
            work=work)

        expected = Document(
            document_xml=document_fixture(
                xml="""
        <section eId="sec_1">
          <num>1.</num>
          <heading>Tester</heading>
          <paragraph eId="sec_1.paragraph-0">
            <content>
              <p>Something to do with <ref href="/akn/za/act/2002/5">Cap. 12</ref>.</p>
            </content>
          </paragraph>
        </section>"""
            ),
            language=self.eng,
            work=work)

        self.finder.find_references_in_document(document)
        root = etree.fromstring(expected.content)
        expected.content = etree.tostring(root, encoding='utf-8').decode('utf-8')
        self.assertEqual(expected.content, document.content)
