# -*- coding: UTF-8 -*-

from django.core.management.base import BaseCommand
from seo.models import get_seo_models, update_callback

class Command(BaseCommand):
    help = 'Dumps the data as a customised python script.'
    args = '[appname ...]'

    def handle(self, *args, **kwargs):
        for model in get_seo_models():
            for instance in model._default_manager.all():
                update_callback(sender=model, instance=instance, created=False)
                #instance.save()
