#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

from django.test import TestCase
from seo.models import MetaData
try:
    import BeautifulSoup
except ImportError:
    BeautifulSoup = None

class SimpleTest(TestCase):
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
