#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from django.db.models.options import get_verbose_name
from django.db import models
from django.utils.datastructures import SortedDict

class Options(object):
    def __init__(self, meta, help_text=None):
        self.use_sites = meta.pop('use_sites', False)
        self.use_i18n = meta.pop('use_i18n', False)
        self.use_redirect = meta.pop('use_redirect', False)
        self.use_cache = meta.pop('use_cache', False)
        self.groups = meta.pop('groups', {})
        self.seo_views = meta.pop('seo_views', [])
        self.verbose_name = meta.pop('verbose_name', None)
        self.verbose_name_plural = meta.pop('verbose_name_plural', None)
        self.backends = list(meta.pop('backends', ('path', 'modelinstance', 'model', 'view')))
        self._set_seo_models(meta.pop('seo_models', []))
        self.bulk_help_text = help_text
        self.original_meta = meta
        self.models = SortedDict()
        self.name = None
        self.elements = None
        self.metadata = None

    def get_model(self, name):
        try:
            return self.models[name]
        except KeyError:
            return None

    def _update_from_name(self, name):
        self.name = name
        self.verbose_name = self.verbose_name or get_verbose_name(name)
        self.verbose_name_plural = self.verbose_name_plural or self.verbose_name + 's'

    def _register_elements(self, elements):
        """ Takes elements from the metadata class and creates a base model for all backend models .
        """
        self.elements = elements

        for key, obj in elements.items():
            obj.contribute_to_class(self.metadata, key)

        # Create the common Django fields
        fields = {}
        for key, obj in elements.items():
            if obj.editable:
                field = obj.get_field()
                if not field.help_text:
                    if key in self.bulk_help_text:
                        field.help_text = self.bulk_help_text[key]
                fields[key] = field

        # 0. Abstract base model with common fields
        base_meta = type('Meta', (), self.original_meta)
        class BaseMeta(base_meta):
            abstract = True
            app_label = 'seo'
        fields['Meta'] = BaseMeta
        # Do we need this?
        fields['__module__'] = __name__ #attrs['__module__']
        self.MetadataBaseModel = type('%sBase' % self.name, (models.Model,), fields)

    def _add_backend(self, backend):
        """ Builds a subclass model for the given backend """
        md_type = backend.verbose_name
        base = backend().get_model(self)
        # TODO: Rename this field
        new_md_attrs = {'_metadata': self.metadata, '__module__': __name__ }

        new_md_meta = {}
        new_md_meta['verbose_name'] = '%s (%s)' % (self.verbose_name, md_type)
        new_md_meta['verbose_name_plural'] = '%s (%s)' % (self.verbose_name_plural, md_type)
        new_md_meta['unique_together'] = base._meta.unique_together
        new_md_attrs['Meta'] = type("Meta", (), new_md_meta)
        new_md_attrs['_metadata_type'] = backend.name
        model = type("%s%s"%(self.name,"".join(md_type.split())), (base, self.MetadataBaseModel), new_md_attrs.copy())
        self.models[backend.name] = model
        # This is a little dangerous, but because we set __module__ to __name__, the model needs tobe accessible here
        globals()[model.__name__] = model

    def _set_seo_models(self, value):
        """ Gets the actual models to be used. """
        seo_models = []
        for model_name in value:
            if "." in model_name:
                app_label, model_name = model_name.split(".", 1)
                model = models.get_model(app_label, model_name)
                if model:
                    seo_models.append(model)
            else:
                app = models.get_app(model_name)
                if app:
                    seo_models.extend(models.get_models(app))
    
        self.seo_models = seo_models


