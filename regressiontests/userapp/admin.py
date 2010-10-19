#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from rollyourown.seo.admin import register_seo_admin, get_inline
from django.contrib import admin
from userapp.seo import Coverage, WithSites

register_seo_admin(admin.site, Coverage)
register_seo_admin(admin.site, WithSites)

from userapp.models import Product, Page, Category

class WithMetaDataAdmin(admin.ModelAdmin):
    inlines = [get_inline(Coverage), get_inline(WithSites)]

admin.site.register(Product, WithMetaDataAdmin)
admin.site.register(Page, WithMetaDataAdmin)

from rollyourown.seo.default import DefaultMetaData
register_seo_admin(admin.site, DefaultMetaData)
