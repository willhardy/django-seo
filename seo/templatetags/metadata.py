#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django import template
from django.template.context import Context
from django.template.loader import get_template
from seo.models import template_meta_data

register = template.Library()

class MetaDataNode(template.Node):
    def __init__(self, variable_name):
        self.variable_name = variable_name
        self.meta_data = template.Variable(CONTEXT_VARIABLE)
        self.request = template.Variable('request')

    def render(self, context):
        variable_name = self.variable_name or CONTEXT_VARIABLE
        meta_data = self.meta_data.resolve(context)
        request = self.request.resolve(context)
        if not meta_data and not request:
            raise template.TemplateSyntaxError("Need RequestContext or meta_data object as a variable '%s'" % CONTEXT_VARIABLE)
        elif not meta_data and request:
            meta_data = template_meta_data(request)
        if meta_data is not None:
            meta_data.resolve(context)
            context[variable_name] = meta_data

        return ""


from seo.models import CONTEXT_VARIABLE

def do_get_metadata(parser, token):
    """
    Retrieve an object which can produce (and format) meta data.

        {% get_metadata [as my_variable] %}

    """
    bits = list(token.split_contents())

    if len(bits) == 1:
        variable_name = None
    elif len(bits) == 3 and bits[1] == "as":
        variable_name = bits[2]
    else:
        raise template.TemplateSyntaxError("expected format is '%r [as <variable_name>]'" % bits[0])

    return MetaDataNode(variable_name)


register.tag('get_metadata', do_get_metadata)

