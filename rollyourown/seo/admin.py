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

class PathMetadataAdmin(admin.ModelAdmin):
    list_display = ('_path',)

class ModelInstanceMetadataAdmin(admin.ModelAdmin):
    list_display = ('_path', '_content_type', '_object_id')

class ModelMetadataAdmin(admin.ModelAdmin):
    list_display = ('_content_type',)

class ViewMetadataAdmin(admin.ModelAdmin):
    list_display = ('_view', )


# Varients with sites support

class SitePathMetadataAdmin(admin.ModelAdmin):
    list_display = ('_path', '_site')
    list_filter = ('_site',)

class SiteModelInstanceMetadataAdmin(admin.ModelAdmin):
    list_display = ('_path', '_content_type', '_object_id', '_site')
    list_filter = ('_site', '_content_type')

class SiteModelMetadataAdmin(admin.ModelAdmin):
    list_display = ('_content_type', '_site')
    list_filter = ('_site',)

class SiteViewMetadataAdmin(admin.ModelAdmin):
    list_display = ('_view', '_site')
    list_filter = ('_site',)


def register_seo_admin(admin_site, metadata_class):
    if metadata_class.use_sites:
        path_admin = SitePathMetadataAdmin
        model_instance_admin = SiteModelInstanceMetadataAdmin
        model_admin = SiteModelMetadataAdmin
        view_admin = SiteViewMetadataAdmin
    else:
        path_admin = PathMetadataAdmin
        model_instance_admin = ModelInstanceMetadataAdmin
        model_admin = ModelMetadataAdmin
        view_admin = ViewMetadataAdmin

    class ModelAdmin(model_admin):
        form = get_model_form(metadata_class)

    admin_site.register(metadata_class.PathMetadata, path_admin)
    admin_site.register(metadata_class.ModelInstanceMetadata, model_instance_admin)
    admin_site.register(metadata_class.ModelMetadata, ModelAdmin)
    admin_site.register(metadata_class.ViewMetadata, view_admin)


def get_inline(metadata_class):
    attrs = {'max_num': 1, 'model': metadata_class.ModelInstanceMetadata}
    return type('MetadataInline', (generic.GenericStackedInline,), attrs)


def get_model_form(metadata_class):
    # Restrict conetnt type choices to the models set in seo_models
    seo_models = _get_seo_models(metadata_class)
    content_type_choices = [(x._get_pk_val(), smart_unicode(x)) for x in ContentType.objects.filter(id__in=get_seo_content_types(seo_models))]

    class ModelMetadataForm(forms.ModelForm):
        content_type = forms.ChoiceField(choices=content_type_choices)

        class Meta:
            model = metadata_class.ModelMetadata

    return ModelMetadataForm
