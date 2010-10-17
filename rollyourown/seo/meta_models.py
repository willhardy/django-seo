#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db import models
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
#from rollyourown.seo.modelmetadata import get_seo_content_types
from rollyourown.seo.systemviews import SystemViewField
from rollyourown.seo.utils import resolve_to_name

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


# 1. Path-based model
class PathMetaDataBase(models.Model):
    path    = models.CharField(_('path'), max_length=511)
    objects = PathMetaDataManager()

    class Meta:
        verbose_name = _('path-based metadata')
        verbose_name_plural = _('path-based metadata')
        abstract = True

# 2. Model-based model
class ModelMetaDataBase(models.Model):
    content_type   = models.ForeignKey(ContentType, null=True, blank=True)
                                #limit_choices_to={'id__in': get_seo_content_types(new_class)})
    objects        = ModelMetaDataManager()

    def _set_context(self, instance):
        """ Use the given model instance as context for rendering 
            any substitutions. 
        """
        self.__instance = instance

    def __getattribute__(self, name):
        # Any values coming from elements should be parsed and resolved.
        value = super(ModelMetaDataBase, self).__getattribute__(name)
        if (name in (f.name for f in super(ModelMetaDataBase, self).__getattribute__('_meta').fields) 
            and '_ModelMetaData__instance' in super(ModelMetaDataBase, self).__getattribute__('__dict__')):
            instance = super(ModelMetaDataBase, self).__getattribute__('_ModelMetaData__instance')
            return _resolve(value, instance)
        else: 
            return value

    class Meta:
        verbose_name = _('model-based metadata')
        verbose_name_plural = _('model-based metadata')
        abstract = True

# 3. Model-instance-based model
class ModelInstanceMetaDataBase(models.Model):
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
class ViewMetaDataBase(models.Model):
    view = SystemViewField(blank=True, null=True)
    objects = ViewMetaDataManager()

    class Meta:
        verbose_name = _('view-based metadata')
        verbose_name_plural = _('view-based metadata')
        abstract = True
