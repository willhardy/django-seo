# -*- coding: UTF-8 -*-

from django.conf import settings
from django.db import models
from django.contrib.contenttypes.models import ContentType

setting_name_seo_models = "SEO_MODELS"

def get_seo_models():
    """ Returns a list of models that are defined in settings (SEO_MODELS)
    """
    seo_models = []
    for model_name in getattr(settings, setting_name_seo_models, ()):
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

def get_seo_content_types():
    """ Returns a list of content types from the models defined in settings (SEO_MODELS) """
    return [ ContentType.objects.get_for_model(m) for m in get_seo_models() ]
