# -*- coding: UTF-8 -*-

from django.core.management.base import BaseCommand
from seo.models import get_seo_models, update_callback, MetaData
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Dumps the data as a customised python script.'

    def handle(self, *args, **kwargs):
        add_only = True

        for model in get_seo_models():
            content_type = ContentType.objects.get_for_model(model)
            instances = model._default_manager.all()
            if add_only:
                # Exclude anything that's preexisting, there shouldn't be too many objects (ie 000s) for the given models
                preexisting_ids = MetaData.objects.filter(content_type=content_type).values_list('object_id', flat=True)
                instances = instances.exclude(pk__in=preexisting_ids)

            print "Adding %d instances from %s.%s" % (instances.count(), model._meta.app_label, model._meta.object_name)

            for instance in instances:
                update_callback(sender=model, instance=instance, created=False)
