#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db import models
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.template import Template, Context

#from rollyourown.seo.modelmetadata import get_seo_content_types
from rollyourown.seo.systemviews import SystemViewField
from rollyourown.seo.utils import resolve_to_name, NotSet, Literal

class MetaDataManager(models.Manager):
    def on_current_site(self):
        queryset = super(MetaDataManager, self).get_query_set()
        # If we are using sites, exclude irrelevant data
        if self.model._meta_data.use_sites:
            # Exclude entries for other sites, keep site=current and site=null
            queryset = queryset.extra(where=['site_id IS NULL OR site_id=%s'], params=[settings.SITE_ID])
        return queryset

class PathMetaDataManager(MetaDataManager):
    def get_from_path(self, path):
        return self.on_current_site().get(path=path)

class ModelMetaDataManager(MetaDataManager):
    def get_from_content_type(self, content_type):
        return self.on_current_site().get(content_type=content_type)

class ModelInstanceMetaDataManager(MetaDataManager):
    def get_from_path(self, path):
        return self.on_current_site().get(path=path)

class ViewMetaDataManager(MetaDataManager):
    def get_from_path(self, path):
        view_name = resolve_to_name(path)
        if view_name is not None:
            return self.on_current_site().get(view=view_name)
        raise self.model.DoesNotExist()

class MetaDataBaseModel(models.Model):

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(MetaDataBaseModel, self).__init__(*args, **kwargs)

        # Provide access to a class instance
        self._meta_data = self.__class__._meta_data()

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
    path    = models.CharField(_('path'), max_length=511)
    objects = PathMetaDataManager()

    class Meta:
        verbose_name = _('path-based metadata')
        verbose_name_plural = _('path-based metadata')
        abstract = True

# 2. Model-based model
class ModelMetaDataBase(MetaDataBaseModel):
    content_type   = models.ForeignKey(ContentType, null=True, blank=True)
                                #limit_choices_to={'id__in': get_seo_content_types(new_class)})
    objects        = ModelMetaDataManager()

    def _set_context(self, instance):
        """ Use the given model instance as context for rendering 
            any substitutions. 
        """
        self.__instance = instance

    def _resolve_value(self, name):
        value = super(ModelMetaDataBase, self)._resolve_value(name)
        return _resolve(value, self.__instance)

    class Meta:
        verbose_name = _('model-based metadata')
        verbose_name_plural = _('model-based metadata')
        abstract = True

# 3. Model-instance-based model
class ModelInstanceMetaDataBase(MetaDataBaseModel):
    path           = models.CharField(_('path'), max_length=511)
    content_type   = models.ForeignKey(ContentType, null=True, blank=True)
                                #limit_choices_to={'id__in': get_seo_content_types(new_class)})
    object_id      = models.PositiveIntegerField(null=True, blank=True, editable=False)
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    objects        = ModelInstanceMetaDataManager()

    class Meta:
        verbose_name = _('model-instance-based metadata')
        verbose_name_plural = _('model-instance-based metadata')
        unique_together = ('content_type', 'object_id')
        abstract = True

# 4. View-based model
class ViewMetaDataBase(MetaDataBaseModel):
    view = SystemViewField(blank=True, null=True)
    objects = ViewMetaDataManager()

    class Meta:
        verbose_name = _('view-based metadata')
        verbose_name_plural = _('view-based metadata')
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

