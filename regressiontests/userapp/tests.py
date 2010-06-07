#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from seo.models import MetaData
from userapp.models import Page
try:
    import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class ContentTypes(TestCase):
    """ A set of unit tests that check the usage of content types. """

    def setUp(self):
        self.page1 = Page.objects.create(title=u"MD Page One Title", type=u"page one type", content=u"Page one content.")
        self.page2 = Page.objects.create(type=u"page two type", content=u"Page two content.")

        content_type = ContentType.objects.get_for_model(Page)

        self.meta_data1 = MetaData.objects.get(content_type=content_type, object_id=self.page1.id)
        self.meta_data1.keywords = "MD Keywords"
        self.meta_data1.save()
        self.meta_data2 = MetaData.objects.get(content_type=content_type, object_id=self.page2.id)

        self.category_meta_data = MetaData(content_type=content_type, object_id=None)
        self.category_meta_data.title = u"CMD { Title"
        self.category_meta_data.keywords = u"CMD Keywords, {{ page.type }}, more keywords"
        self.category_meta_data.description = u"CMD Description for {{ page }} and {{ page }}"
        self.category_meta_data.save()

        self.context1 = self.meta_data1.context['seo_meta_data']
        self.context2 = self.meta_data2.context['seo_meta_data']

    def test_direct_data(self):
        """ Check data is used directly when it is given. """
        self.assertEqual(self.context1.title, u'MD Page One Title')
        self.assertEqual(self.context1.keywords, u'MD Keywords')

    def test_category_data(self):
        """ Check that the category data is used when it is missing from the relevant meta data. 
        """
        # The brace is included to check that no error is thrown by an attempted substitution
        self.assertEqual(self.context2.title, u'CMD { Title')

    def test_category_substitution(self):
        """ Check that category data is substituted correctly """
        self.assertEqual(self.context2.keywords, u'CMD Keywords, page two type, more keywords')
        self.assertEqual(self.context1.description, u'CMD Description for MD Page One Title and MD Page One Title')
        self.assertEqual(self.context2.description, u'CMD Description for Page two content. and Page two content.')

class Formatting(TestCase):
    """ A set of simple unit tests that check formatting. """
    def setUp(self):
        self.meta_data = MetaData(
                path        = "/",
                title       = "The <strong>Title</strong>",
                heading     = "The <em>Heading</em>",
                keywords    = 'Some, keywords", with\n other, chars\'',
                description = "A \n description with \" interesting\' chars.",
                extra       = '<meta name="author" content="seo" /><hr /> ' 
                              'No text outside tags please.')
        self.meta_data.save()

        self.context = self.meta_data.context['seo_meta_data']
    
    def test_html(self):
        """ Tests html generation is performed correctly.
            Thorough cleaning is done when BeautifulSoup is available.
        """
        if BeautifulSoup:
            assert self.meta_data.html == """<title>The <strong>Title</strong></title>
<meta name="keywords" content="Some, keywords&#34;, with,  other, chars'" />
<meta name="description" content="A   description with &#34; interesting' chars." />
<meta name="author" content="seo" />
""", "Incorrect html:\n" + self.meta_data.html
        else:
            assert self.meta_data.html == """<title>The <strong>Title</strong></title>
<meta name="keywords" content="Some, keywords&#34;, with,  other, chars'" />
<meta name="description" content="A   description with &#34; interesting' chars." />
<meta name="author" content="seo" /><hr /> No text outside tags please.
""", "Incorrect html:\n" + self.meta_data.html

    def test_description(self):
        """ Tests the description is cleaned correctly. """
        exp = "A   description with &#34; interesting' chars."
        self.assertEqual(self.context.description, exp)

    def test_keywords(self):
        """ Tests keywords are cleaned correctly. """
        exp = "Some, keywords&#34;, with,  other, chars'"
        self.assertEqual(self.context.keywords, exp)

    def test_title(self):
        """ Tests the title is cleaned correctly. """
        exp = 'The <strong>Title</strong>'
        self.assertEqual(self.context.title, exp)

    def test_heading(self):
        """ Tests the heading is cleaned correctly. """
        exp = 'The <em>Heading</em>'
        self.assertEqual(self.context.heading, exp)

    def test_extra(self):
        """ Tests the extras attribute is cleaned correctly. 
            Thorough cleaning is done when BeautifulSoup is available.
        """
        if BeautifulSoup:
            exp = '<meta name="author" content="seo" />'
        else:
            exp = ('<meta name="author" content="seo" /><hr />'
                  ' No text outside tags please.')
        self.assertEqual(self.context.extra, exp)


class Random(TestCase):
    """ A collection of random tests for various isolated features. """

    def setUp(self):
        self.page = Page.objects.create()
        self.content_type = ContentType.objects.get_for_model(Page)
        self.meta_data = MetaData.objects.get(content_type=self.content_type,
                                                    object_id=self.page.id)
        self.context = self.meta_data.context['seo_meta_data']

    def test_default_fallback(self):
        """ Tests the ability to use the current Site name as a default 
            fallback. 
        """
        from django.contrib.sites.models import Site
        site = Site.objects.get_current()
        self.assertEqual(site.name, self.context.title)

    def test_missing_category_meta_data(self):
        " Checks that lookups work where the category meta data is  missing "
        try:
            self.context.title
        except MetaData.DoesNotExist:
            self.fail("MetaData.DoesNotExist raised inappropriately.")

