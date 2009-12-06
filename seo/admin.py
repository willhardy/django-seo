# -*- coding: UTF-8 -*-

from django.contrib import admin
from seo import models

class MetaDataAdmin(admin.ModelAdmin):
    list_display = ('path', 'title', 'content_type', )#'keywords', 'description', 'content_type')
    list_editable = ('title', )#'keywords', 'description')
    list_filter = ('content_type',)
    search_fields = ('title', 'keywords', 'description')

admin.site.register(models.MetaData, MetaDataAdmin)
