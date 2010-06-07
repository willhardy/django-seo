# -*- coding: utf-8 -*-

import logging
from django.conf import settings
from django.db import models

setting_name_seo_models = "SEO_MODELS"

def get_seo_models():
    """ Returns a list of models that are defined in settings (SEO_MODELS)
    """
    seo_models = []
    for model_name in getattr(settings, setting_name_seo_models, ()):
        if "." in model_name:
            # TODO: Test this block
            app_label, model_name = model_name.split(".", 1)
            model = models.get_model(app_label, model_name)
            if model:
                seo_models.append(model)
        else:
            app = models.get_app(model_name)
            if app:
                seo_models.extend(models.get_models(app))

    return seo_models

def get_seo_content_types():
    """ Returns a list of content types from the models defined in settings (SEO_MODELS) """
    # TODO: Test this function
    from django.contrib.contenttypes.models import ContentType
    logging.debug("Populating content type choices.")
    return [ ContentType.objects.get_for_model(m) for m in get_seo_models() ]

class SEO_CONTENT_TYPE_CHOICES(dict):
    """ Class to lazily populate the choices for content types (they wont be there before a syncdb). 
        Items are populated on first interaction (getattr or len) with dict.

        TODO: Test this class
    """
    def _populate_content_types(self):
        if not super(SEO_CONTENT_TYPE_CHOICES, self).__len__():
            self['id__in'] = [ct.id for ct in get_seo_content_types()]

    def __getitem__(self, key):
        self._populate_content_types()
        return super(SEO_CONTENT_TYPE_CHOICES, self).__getitem__(key)

    def __len__(self):
        self._populate_content_types()
        return super(SEO_CONTENT_TYPE_CHOICES, self).__len__()

    def __iter__(self):
        self._populate_content_types()
        return super(SEO_CONTENT_TYPE_CHOICES, self).__iter__()

SEO_CONTENT_TYPE_CHOICES = SEO_CONTENT_TYPE_CHOICES()

