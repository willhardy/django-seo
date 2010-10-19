# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.contenttypes import generic

# Varients without sites support

class PathMetaDataAdmin(admin.ModelAdmin):
    list_display = ('path',)

class ModelInstanceMetaDataAdmin(admin.ModelAdmin):
    list_display = ('path', 'content_type', 'object_id')

class ModelMetaDataAdmin(admin.ModelAdmin):
    list_display = ('content_type',)

class ViewMetaDataAdmin(admin.ModelAdmin):
    list_display = ('view', )


# Varients with sites support

class SitePathMetaDataAdmin(admin.ModelAdmin):
    list_display = ('path', 'site')
    list_filter = ('site',)

class SiteModelInstanceMetaDataAdmin(admin.ModelAdmin):
    list_display = ('path', 'content_type', 'object_id', 'site')
    list_filter = ('site', 'content_type')

class SiteModelMetaDataAdmin(admin.ModelAdmin):
    list_display = ('content_type', 'site')
    list_filter = ('site',)

class SiteViewMetaDataAdmin(admin.ModelAdmin):
    list_display = ('view', 'site')
    list_filter = ('site',)


def register_seo_admin(admin_site, meta_data_class):
    if meta_data_class.use_sites:
        admin_site.register(meta_data_class.PathMetaData, SitePathMetaDataAdmin)
        admin_site.register(meta_data_class.ModelInstanceMetaData, SiteModelInstanceMetaDataAdmin)
        admin_site.register(meta_data_class.ModelMetaData, SiteModelMetaDataAdmin)
        admin_site.register(meta_data_class.ViewMetaData, SiteViewMetaDataAdmin)
    else:
        admin_site.register(meta_data_class.PathMetaData, PathMetaDataAdmin)
        admin_site.register(meta_data_class.ModelInstanceMetaData, ModelInstanceMetaDataAdmin)
        admin_site.register(meta_data_class.ModelMetaData, ModelMetaDataAdmin)
        admin_site.register(meta_data_class.ViewMetaData, ViewMetaDataAdmin)


def get_inline(meta_data_class):
    attrs = {'max_num': 1, 'model': meta_data_class.ModelInstanceMetaData}
    return type('MetaDataInline', (generic.GenericStackedInline,), attrs)

