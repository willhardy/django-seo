# -*- coding: utf-8 -*-

from seo.models import MetaData, CONTEXT_VARIABLE

def seo(request):
    try:
        return {CONTEXT_VARIABLE: MetaData.objects.template_meta_data(request)}
    except MetaData.DoesNotExist:
        return MetaData().context
