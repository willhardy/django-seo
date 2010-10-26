#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from rollyourown import seo
from django.conf import settings

class DefaultMetadata(seo.Metadata):
    """ A very basic default class for those who do not wish to write their own.
    """
    title       = seo.Tag(head=True, max_length=68)
    keywords    = seo.MetaTag()
    description = seo.MetaTag(max_length=155)
    heading     = seo.Tag(name="h1")

    class Meta:
        verbose_name = "Metadata"
        verbose_name_plural = "Metadata"
        use_sites = False
        # This default class is automatically created when SEO_MODELS is 
        # defined, so we'll take our model list from there.
        seo_models = getattr(settings, 'SEO_MODELS', [])

    class HelpText:
        title       = "This is the page title, that appears in the title bar."
        keywords    = "Comma-separated keywords for search engines."
        description = "A short description, displayed in search results."
        heading     = "This is the page heading, appearing in the &lt;h1&gt; tag."

