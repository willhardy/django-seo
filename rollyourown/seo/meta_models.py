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

RESERVED_FIELD_NAMES = ('_metadata', '_path', '_content_type', '_object_id',
                        '_content_object', '_view', '_site', 'objects', 
                        '_resolve_value', '_set_context', 'id', 'pk' )


class MetadataBaseModel(models.Model):

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(MetadataBaseModel, self).__init__(*args, **kwargs)

        # Provide access to a class instance
        # TODO Rename to __metadata
        self._metadata = self.__class__._metadata()

    # TODO Rename to __resolve_value?
    def _resolve_value(self, name):
        """ Returns an appropriate value for the given name. """
        name = str(name)
        if name in self._metadata._meta.elements:
            element = self._metadata._meta.elements[name]

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
                    return populate_from(self._metadata)
            elif isinstance(populate_from, Literal):
                return populate_from.value
            elif populate_from is not NotSet:
                return self._resolve_value(populate_from)

        # If this is not an element, look for an attribute on metadata
        try:
            value = getattr(self._metadata, name)
        except AttributeError:
            pass
        else:
            if callable(value):
                if getattr(value, 'im_self', None):
                    return value()
                else:
                    return value(self._metadata)
            return value


class BaseManager(models.Manager):
    def on_current_site(self, site=None):
        if isinstance(site, Site):
            site_id = site.id
        elif site is not None:
            site_id = site and Site.objects.get(domain=site).id
        else:
            site_id = settings.SITE_ID
        # Exclude entries for other sites
        where = ['_site_id IS NULL OR _site_id=%s']
        return self.get_query_set().extra(where=where, params=[site_id])

    def for_site_and_language(self, site=None, language=None):
        queryset = self.on_current_site(site)
        if language:
            queryset = queryset.filter(_language=language)
        return queryset

# Following is part of an incomplete move to define backends, which will:
#   -  contain the business logic of backends to a short, succinct module
#   -  allow individual backends to be turned on and off
#   -  allow new backends to be added by end developers
#
# A Backend:
#   -  defines an abstract base class for storing the information required to associate metadata with its target (ie a view, a path, a model instance etc)
#   -  defines a method for retrieving an instance
#
# This is not particularly easy.
#   -  unique_together fields need to be defined in the same django model, as some django versions don't enforce the uniqueness when it spans subclasses
#   -  most backends use the path to find a matching instance. The model backend however ideally needs a content_type (found from a model instance backend, which used the path)
#   -  catering for all the possible options (use_sites, use_languages), needs to be done succiently, and at compile time
#
# This means that:
#   -  all fields that share uniqueness (backend fields, _site, _language) need to be defined in the same model
#   -  as backends should have full control over the model, therefore every backend needs to define the compulsory fields themselves (eg _site and _language).
#      There is no way to add future compulsory fields to all backends without editing each backend individually. 
#      This is probably going to have to be a limitataion we need to live with.

class MetadataBackend(object):
    name = None
    verbose_name = None
    unique_together = None

    def get_unique_together(self, options):
        ut = []
        for ut_set in self.unique_together:
            ut_set = [a for a in ut_set]
            if options.use_sites:
                ut_set.append('_site')
            if options.use_i18n:
                ut_set.append('_language')
            ut.append(tuple(ut_set))
        return tuple(ut)

    def get_manager(self, options):
        _get_instances = self.get_instances

        class _Manager(BaseManager):
            def get_instances(self, path, site=None, language=None, context=None):
                queryset = self.for_site_and_language(site, language)
                return _get_instances(queryset, path, context)

            if not options.use_sites:
                def for_site_and_language(self, site=None, language=None):
                    queryset = self.get_query_set()
                    if language:
                        queryset = queryset.filter(_language=language)
                    return queryset
        return _Manager


class PathBackend(MetadataBackend):
    name = "path"
    verbose_name = "Path"
    unique_together = (("_path",),)

    def get_instances(self, queryset, path, context):
        return queryset.filter(_path=path)

    def get_model(self, options):
        class PathMetadataBase(MetadataBaseModel):
            _path = models.CharField(_('path'), max_length=511, unique=not (options.use_sites or options.use_i18n))
            if options.use_sites:
                _site = models.ForeignKey(Site, null=True, blank=True)
            if options.use_i18n:
                _language = models.CharField(max_length=5, null=True, blank=True, db_index=True)
            objects = self.get_manager(options)()

            def __unicode__(self):
                return self._path

            class Meta:
                abstract = True
                unique_together = self.get_unique_together(options)

        return PathMetadataBase


class ViewBackend(MetadataBackend):
    name = "view"
    verbose_name = "View"
    unique_together = (("_view",),)

    def get_instances(self, queryset, path, context):
        view_name = resolve_to_name(path)
        if view_name is not None:
            return queryset.filter(_view=view_name)

    def get_model(self, options):
        class ViewMetadataBase(MetadataBaseModel):
            _view = SystemViewField(unique=not (options.use_sites or options.use_i18n))
            if options.use_sites:
                _site = models.ForeignKey(Site, null=True, blank=True)
            if options.use_i18n:
                _language = models.CharField(max_length=5, null=True, blank=True, db_index=True)
            objects = self.get_manager(options)()

            def _process_context(self, context):
                """ Use the context when rendering any substitutions.  """
                if 'view_context' in context:
                    self.__context = context['view_context']
        
            def _resolve_value(self, name):
                value = super(ViewMetadataBase, self)._resolve_value(name)
                try:
                    return _resolve(value, context=self.__context)
                except AttributeError:
                    return value

            def __unicode__(self):
                return self._view
    
            class Meta:
                abstract = True
                unique_together = self.get_unique_together(options)

        return ViewMetadataBase


class ModelInstanceBackend(MetadataBackend):
    name = "modelinstance"
    verbose_name = "Model Instance"
    unique_together = (("_path",), ("_content_type", "_object_id"))

    def get_instances(self, queryset, path, context):
        return queryset.filter(_path=path)

    def get_model(self, options):
        class ModelInstanceMetadataBase(MetadataBaseModel):
            _path = models.CharField(_('path'), max_length=511, unique=not (options.use_sites or options.use_i18n))
            _content_type = models.ForeignKey(ContentType, editable=False)
            _object_id = models.PositiveIntegerField(editable=False)
            _content_object = generic.GenericForeignKey('_content_type', '_object_id')
            if options.use_sites:
                _site = models.ForeignKey(Site, null=True, blank=True)
            if options.use_i18n:
                _language = models.CharField(max_length=5, null=True, blank=True, db_index=True)
            objects = self.get_manager(options)()
        
            def __unicode__(self):
                return self._path

            class Meta:
                unique_together = self.get_unique_together(options)
                abstract = True

            def _process_context(self, context):
                context['content_type'] = self._content_type
                context['model_instance'] = self

        return ModelInstanceMetadataBase


class ModelBackend(MetadataBackend):
    name = "model"
    verbose_name = "Model"
    unique_together = (("_content_type",),)

    def get_instances(self, queryset, path, context):
        if context and 'content_type' in context:
            return queryset.filter(_content_type=context['content_type'])

    def get_model(self, options):
        class ModelMetadataBase(MetadataBaseModel):
            _content_type = models.ForeignKey(ContentType)
            if options.use_sites:
                _site = models.ForeignKey(Site, null=True, blank=True)
            if options.use_i18n:
                _language = models.CharField(max_length=5, null=True, blank=True, db_index=True)
            objects = self.get_manager(options)()

            def __unicode__(self):
                return unicode(self._content_type)

            def _process_context(self, context):
                """ Use the given model instance as context for rendering 
                    any substitutions. 
                """
                if 'model_instance' in context:
                    self.__instance = context['model_instance']
        
            def _resolve_value(self, name):
                value = super(ModelMetadataBase, self)._resolve_value(name)
                try:
                    return _resolve(value, self.__instance._content_object)
                except AttributeError:
                    return value
        
            class Meta:
                abstract = True
                unique_together = self.get_unique_together(options)
        return ModelMetadataBase



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

def _get_seo_models(metadata):
    """ Gets the actual models to be used. """
    seo_models = []
    for model_name in metadata._meta.seo_models:
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
