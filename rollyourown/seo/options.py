#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from django.db.models.options import get_verbose_name

class Options(object):
    def __init__(self, meta):
        self.use_sites = meta.pop('use_sites', False)
        self.use_i18n = meta.pop('use_i18n', False)
        self.use_redirect = meta.pop('use_redirect', False)
        self.use_cache = meta.pop('use_cache', False)
        self.groups = meta.pop('groups', {})
        self.seo_models = meta.pop('seo_models', [])
        self.verbose_name = meta.pop('verbose_name', None)
        self.verbose_name_plural = meta.pop('verbose_name_plural', None)

    def update_from_name(self, name):
        self.verbose_name = self.verbose_name or get_verbose_name(name)
        self.verbose_name_plural = self.verbose_name_plural or self.verbose_name + 's'
