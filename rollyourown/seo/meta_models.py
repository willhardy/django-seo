#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db import models
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.template import Template, Context

from rollyourown.seo.systemviews import SystemViewField
from rollyourown.seo.utils import resolve_to_name, NotSet, Literal

RESERVED_FIELD_NAMES = ('_meta_data', '_path', '_content_type', '_object_id', '_content_object', '_view', '_site', 'objects', '_resolve_value', '_set_context', 'id', 'pk')
# Also Meta, but this is difficult to check

class MetaDataManager(models.Manager):
    def on_current_site(self):
        queryset = super(MetaDataManager, self).get_query_set()
        # If we are using sites, exclude irrelevant data
        if self.model._meta_data.use_sites:
            # Exclude entries for other sites, keep site=current and site=null
            queryset = queryset.extra(where=['_site_id IS NULL OR _site_id=%s'], params=[settings.SITE_ID])
        return queryset

class PathMetaDataManager(MetaDataManager):
    def get_from_path(self, path):
        return self.on_current_site().get(_path=path)

class ModelMetaDataManager(MetaDataManager):
    def get_from_content_type(self, content_type):
        return self.on_current_site().get(_content_type=content_type)

class ModelInstanceMetaDataManager(MetaDataManager):
    def get_from_path(self, path):
        return self.on_current_site().get(_path=path)

class ViewMetaDataManager(MetaDataManager):
    def get_from_path(self, path):
        view_name = resolve_to_name(path)
        if view_name is not None:
            return self.on_current_site().get(_view=view_name)
        raise self.model.DoesNotExist()

class MetaDataBaseModel(models.Model):

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(MetaDataBaseModel, self).__init__(*args, **kwargs)

        # Provide access to a class instance
        # TODO Rename to __meta_data
        self._meta_data = self.__class__._meta_data()

    # TODO Rename to __resolve_value
    def _resolve_value(self, name):
        """ Returns an appropriate value for the given name. """
        name = str(name)
        if name in self._meta_data.elements:
            element = self._meta_data.elements[name]

            # Look in instances for an explicit value
            if element.editable:
                value = getattr(self, name)
                if value:
                    return value

            # Otherwise, return an appropriate default value (populate_from)
            populate_from = element.populate_from
            if callable(populate_from):
                if getattr(populate_from, 'im_self', None):
                    return populate_from()
                else:
                    return populate_from(self._meta_data)
            elif isinstance(populate_from, Literal):
                return populate_from.value
            elif populate_from is not NotSet:
                return self._resolve_value(populate_from)

        # If this is not an element, look for an attribute on metadata
        try:
            value = getattr(self._meta_data, name)
        except AttributeError:
            pass
        else:
            if callable(value):
                if getattr(value, 'im_self', None):
                    return value()
                else:
                    return value(self._meta_data)
            return value



# 1. Path-based model
class PathMetaDataBase(MetaDataBaseModel):
    _path    = models.CharField(_('path'), max_length=511)
    objects = PathMetaDataManager()

    def __unicode__(self):
        return self._path

    class Meta:
        abstract = True

# 2. Model-based model
class ModelMetaDataBase(MetaDataBaseModel):
    _content_type   = models.ForeignKey(ContentType, null=True, blank=True)
    objects        = ModelMetaDataManager()

    def __unicode__(self):
        return unicode(self._content_type)

    def _set_context(self, instance):
        """ Use the given model instance as context for rendering 
            any substitutions. 
        """
        self.__instance = instance

    def _resolve_value(self, name):
        value = super(ModelMetaDataBase, self)._resolve_value(name)
        return _resolve(value, self.__instance)

    class Meta:
        abstract = True

# 3. Model-instance-based model
class ModelInstanceMetaDataBase(MetaDataBaseModel):
    _path           = models.CharField(_('path'), max_length=511)
    _content_type   = models.ForeignKey(ContentType, null=True, blank=True, editable=False)
    _object_id      = models.PositiveIntegerField(null=True, blank=True, editable=False)
    _content_object = generic.GenericForeignKey('_content_type', '_object_id')
    objects        = ModelInstanceMetaDataManager()

    def __unicode__(self):
        return self._path

    class Meta:
        unique_together = ('_content_type', '_object_id')
        abstract = True

# 4. View-based model
class ViewMetaDataBase(MetaDataBaseModel):
    _view = SystemViewField(blank=True, null=True)
    objects = ViewMetaDataManager()

    def __unicode__(self):
        return self._view

    class Meta:
        abstract = True

    def _set_context(self, context):
        """ Use the context when rendering any substitutions.  """
        self.__context = context

    def _resolve_value(self, name):
        value = super(ViewMetaDataBase, self)._resolve_value(name)
        return _resolve(value, context=self.__context)


def _resolve(value, model_instance=None, context=None):
    """ Resolves any template references in the given value. 
    """

    if isinstance(value, basestring) and "{" in value:
        if context is None:
            context = Context()
        if model_instance is not None:
            context[model_instance._meta.module_name] = model_instance
        value = Template(value).render(context)
    return value

def _get_seo_models(meta_data):
    """ Gets the actual models to be used. """
    seo_models = []
    for model_name in meta_data.seo_models:
        if "." in model_name:
            app_label, model_name = model_name.split(".", 1)
            model = models.get_model(app_label, model_name)
            if model:
                seo_models.append(model)
        else:
            app = models.get_app(model_name)
            if app:
                seo_models.extend(models.get_models(app))

    return seo_models

