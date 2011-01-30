#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.db.models import signals
from django.contrib.contenttypes.models import ContentType
from rollyourown.seo.base import registry, populate_metadata
from rollyourown.seo import models as seo_models


def _syncdb_handler(app, created_models, verbosity, **kwargs):
    for Metadata in registry.values():
        InstanceMetadata = Metadata._meta.get_model('modelinstance')
        if InstanceMetadata is not None and InstanceMetadata in created_models:
            for model in Metadata._meta.seo_models:
                content_type = ContentType.objects.get_for_model(model)
                if InstanceMetadata.objects.filter(_content_type=content_type).exists():
                    continue
                if verbosity > 0:
                    print "Populating %s for %s.%s" % (Metadata._meta.verbose_name_plural, model._meta.app_label, model._meta.object_name)
                populate_metadata(model, InstanceMetadata)


def populate_all_metadata():
    """ Create metadata instances for all models in seo_models if empty.
        Once you have created a single metadata instance, this will not run.
        This is because it is a potentially slow operation that need only be
        done once. If you want to ensure that everything is populated, run the
        populate_metadata management command.
    """
    for Metadata in registry.values():
        InstanceMetadata = Metadata._meta.get_model('modelinstance')
        if InstanceMetadata is not None:
            for model in Metadata._meta.seo_models:
                populate_metadata(model, InstanceMetadata)


signals.post_syncdb.connect(_syncdb_handler, sender=seo_models,
            dispatch_uid="rollyourown.seo.management.populate_metadata")
