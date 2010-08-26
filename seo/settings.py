#!/usr/bin/env python

""" Settings with suitable defaults, used by the SEO app.

    You can define the following values in your normal Django settings:

      SEO_DEFAULT_TITLE       The title to use when none is available
      SEO_DEFAULT_KEYWORDS    The keywords to use when none is available
      SEO_DEFAULT_DESCRIPTION The description to use when none is available
      SEO_CONTEXT_VARIABLE    The context variable created by the template tag

    TODO: 
      These will be merged into a single setting, being a dict. This is to
      allow end developers the ability to set defaults for their custom
      fields.
"""

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.functional import lazy

DEFAULT_TITLE       = getattr(settings, "SEO_DEFAULT_TITLE", "")
DEFAULT_KEYWORDS    = getattr(settings, "SEO_DEFAULT_KEYWORDS", "")
DEFAULT_DESCRIPTION = getattr(settings, "SEO_DEFAULT_DESCRIPTION", "")
CONTEXT_VARIABLE    = getattr(settings, "SEO_CONTEXT_VARIABLE", 'seo_meta_data')
TEMPLATE            = "seo/head.html"

# If there is no default title, use a sane fallback
if not DEFAULT_TITLE and Site._meta.installed:
    # Because we are called in models.py, the Site information 
    # wont be available until the tables have been created.
    # The Site information is therefore only looked up when
    # needed.
    def _get_current_site_title():
        current_site = Site.objects.get_current()
        return current_site.name or current_site.domain
    DEFAULT_TITLE = lazy(_get_current_site_title, unicode)()

