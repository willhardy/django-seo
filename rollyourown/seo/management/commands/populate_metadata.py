#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from django.core.management.base import BaseCommand, CommandError
from rollyourown.seo.management import populate_all_metadata

class Command(BaseCommand):
    help = "Populate the database with metadata instances for all models listed in seo_models."

    def handle(self, *args, **options):
        if len(args) > 0:
            raise CommandError("This command currently takes no arguments")

        populate_all_metadata()

