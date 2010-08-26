# -*- coding: utf-8 -*-

from seo.models import MetaData, template_meta_data
from seo.settings import CONTEXT_VARIABLE

def seo(request):
    try:
        return {CONTEXT_VARIABLE: template_meta_data(request.path_info)}
    except MetaData.DoesNotExist:
        return MetaData().context
