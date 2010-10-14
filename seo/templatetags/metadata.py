#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django import template
import logging
from seo.models import get_meta_data
from django.template import VariableDoesNotExist

register = template.Library()

class MetaDataNode(template.Node):
    def __init__(self, variable_name):
        self.variable_name = variable_name
        self.path = template.Variable('request.META.PATH_INFO')

    def render(self, context):
        try:
            path = self.path.resolve(context)
        except VariableDoesNotExist:
            msg = ("{% get_metadata %} needs a RequestContext with the "
                  "'django.core.context_processors.request' context processor.")
            logging.warning(msg) # or is this an error?
        else:
            meta_data = get_meta_data(path)
            if self.variable_name is not None:
                context[self.variable_name] = meta_data
            else:
                return unicode(meta_data)

        return ""


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

