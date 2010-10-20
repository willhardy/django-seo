# -*- coding: utf-8 -*-

from django import forms
from django.contrib import admin
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import smart_unicode

from rollyourown.seo.meta_models import _get_seo_models
from rollyourown.seo.modelmetadata import get_seo_content_types

# TODO Use groups as fieldsets

# Varients without sites support

class PathMetaDataAdmin(admin.ModelAdmin):
    list_display = ('_path',)

class ModelInstanceMetaDataAdmin(admin.ModelAdmin):
    list_display = ('_path', '_content_type', '_object_id')

class ModelMetaDataAdmin(admin.ModelAdmin):
    list_display = ('_content_type',)

class ViewMetaDataAdmin(admin.ModelAdmin):
    list_display = ('_view', )


# Varients with sites support

class SitePathMetaDataAdmin(admin.ModelAdmin):
    list_display = ('_path', '_site')
    list_filter = ('_site',)

class SiteModelInstanceMetaDataAdmin(admin.ModelAdmin):
    list_display = ('_path', '_content_type', '_object_id', '_site')
    list_filter = ('_site', '_content_type')

class SiteModelMetaDataAdmin(admin.ModelAdmin):
    list_display = ('_content_type', '_site')
    list_filter = ('_site',)

class SiteViewMetaDataAdmin(admin.ModelAdmin):
    list_display = ('_view', '_site')
    list_filter = ('_site',)


def register_seo_admin(admin_site, meta_data_class):
    if meta_data_class.use_sites:
        path_admin = SitePathMetaDataAdmin
        model_instance_admin = SiteModelInstanceMetaDataAdmin
        model_admin = SiteModelMetaDataAdmin
        view_admin = SiteViewMetaDataAdmin
    else:
        path_admin = PathMetaDataAdmin
        model_instance_admin = ModelInstanceMetaDataAdmin
        model_admin = ModelMetaDataAdmin
        view_admin = ViewMetaDataAdmin

    class ModelAdmin(model_admin):
        form = get_model_form(meta_data_class)

    admin_site.register(meta_data_class.PathMetaData, path_admin)
    admin_site.register(meta_data_class.ModelInstanceMetaData, model_instance_admin)
    admin_site.register(meta_data_class.ModelMetaData, ModelAdmin)
    admin_site.register(meta_data_class.ViewMetaData, view_admin)


def get_inline(meta_data_class):
    attrs = {'max_num': 1, 'model': meta_data_class.ModelInstanceMetaData}
    return type('MetaDataInline', (generic.GenericStackedInline,), attrs)


def get_model_form(meta_data_class):
    # Restrict conetnt type choices to the models set in seo_models
    seo_models = _get_seo_models(meta_data_class)
    content_type_choices = [(x._get_pk_val(), smart_unicode(x)) for x in ContentType.objects.filter(id__in=get_seo_content_types(seo_models))]

    class ModelMetaDataForm(forms.ModelForm):
        content_type = forms.ChoiceField(choices=content_type_choices)

        class Meta:
            model = meta_data_class.ModelMetaData

    return ModelMetaDataForm
