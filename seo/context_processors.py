# -*- coding: UTF-8 -*-

from seo.models import MetaData

def seo(request):
    try:
        meta_data = MetaData.objects.get(path=request.path)
        return meta_data.context
    except MetaData.DoesNotExist:
        return {}
