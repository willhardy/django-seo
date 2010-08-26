#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django import template
import logging
from django.template.context import Context
from django.template.loader import get_template
from seo.models import template_meta_data
from django.template import VariableDoesNotExist
from seo.settings import CONTEXT_VARIABLE

register = template.Library()

class MetaDataNode(template.Node):
    def __init__(self, variable_name):
        self.variable_name = variable_name
        self.meta_data = template.Variable(CONTEXT_VARIABLE)
        self.path = template.Variable('request.META.PATH_INFO')

    def render(self, context):
        variable_name = self.variable_name or CONTEXT_VARIABLE
        try:
            path = self.path.resolve(context)
        except VariableDoesNotExist:
            path = None

        try:
            meta_data = self.meta_data.resolve(context)
        except VariableDoesNotExist:
            meta_data = template_meta_data(path)
            if path is None:
                msg = ("Need RequestContext with either the "
                      "'django.core.context_processors.request' or "
                      "'seo.context_processors.metadata' context processor"
                      "or a MetaData object as a variable "
                      "called '%s'" % CONTEXT_VARIABLE)
                logging.warning(msg)

        if meta_data is not None:
            meta_data.resolve(context)
            context[variable_name] = meta_data

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

