# -*- coding: utf-8 -*-

from django import forms
from django.contrib import admin
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import smart_unicode

from rollyourown.seo.utils import get_seo_content_types
from rollyourown.seo.systemviews import get_seo_views

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
    if metadata_class._meta.use_sites:
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

    class ViewAdmin(view_admin):
        form = get_view_form(metadata_class)

    admin_site.register(metadata_class._meta.get_model('path'), path_admin)
    admin_site.register(metadata_class._meta.get_model('modelinstance'), model_instance_admin)
    admin_site.register(metadata_class._meta.get_model('model'), ModelAdmin)
    admin_site.register(metadata_class._meta.get_model('view'), ViewAdmin)


def get_inline(metadata_class):
    attrs = {'max_num': 1, 'model': metadata_class._meta.get_model('modelinstance')}
    return type('MetadataInline', (generic.GenericStackedInline,), attrs)


def get_model_form(metadata_class):
    # Restrict content type choices to the models set in seo_models
    content_types = get_seo_content_types(metadata_class._meta.seo_models)
    content_type_choices = [(x._get_pk_val(), smart_unicode(x)) for x in ContentType.objects.filter(id__in=content_types)]

    class ModelMetadataForm(forms.ModelForm):
        _content_type = forms.ChoiceField(choices=content_type_choices)

        class Meta:
            model = metadata_class._meta.get_model('model')

    return ModelMetadataForm


def get_view_form(metadata_class):
    # Restrict content type choices to the models set in seo_models
    view_choices = [(key, " ".join(key.split("_"))) for key in get_seo_views(metadata_class)]

    class ModelMetadataForm(forms.ModelForm):
        _view = forms.ChoiceField(choices=view_choices)

        class Meta:
            model = metadata_class._meta.get_model('model')

    return ModelMetadataForm
