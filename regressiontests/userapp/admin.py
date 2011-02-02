#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from rollyourown.seo.admin import register_seo_admin, get_inline
from django.contrib import admin
from userapp.seo import Coverage, WithSites, WithSEOModels

register_seo_admin(admin.site, Coverage)
register_seo_admin(admin.site, WithSites)

from userapp.models import Product, Page, Category, Tag, NoPath

class WithMetadataAdmin(admin.ModelAdmin):
    inlines = [get_inline(Coverage), get_inline(WithSites)]

admin.site.register(Product, admin.ModelAdmin)
admin.site.register(Page, admin.ModelAdmin)
admin.site.register(Tag, WithMetadataAdmin)
admin.site.register(NoPath, WithMetadataAdmin)


# Register alternative site here to avoid double import
alternative_site = admin.AdminSite()
from rollyourown.seo.admin import auto_register_inlines
#from userapp.models import Tag, Page, Product
#from userapp.seo import Coverage, WithSites, WithSEOModels
alternative_site.register(Tag)
auto_register_inlines(alternative_site, Coverage)
alternative_site.register(Page)
auto_register_inlines(alternative_site, WithSites)
auto_register_inlines(alternative_site, WithSEOModels)
alternative_site.register(Product)

