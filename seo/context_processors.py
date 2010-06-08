# -*- coding: utf-8 -*-

from seo.models import MetaData, template_meta_data, CONTEXT_VARIABLE

def seo(request):
    try:
        return {CONTEXT_VARIABLE: template_meta_data(request)}
    except MetaData.DoesNotExist:
        return MetaData().context
