#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django import template
import logging
from rollyourown.seo import get_meta_data
from django.template import VariableDoesNotExist

register = template.Library()

class MetaDataNode(template.Node):
    def __init__(self, meta_data_name, variable_name, path, site, language):
        self.meta_data_name = meta_data_name
        self.variable_name = variable_name
        self.path = template.Variable(path or 'request.META.PATH_INFO')
        self.site = site and template.Variable(site) or None
        self.language = language and template.Variable(language) or None

    def render(self, context):
        try:
            path = self.path.resolve(context)
            if hasattr(path, 'get_absolute_url'):
                path = path.get_absolute_url
            if 'get_absolute_url' in path:
                path = path['get_absolute_url']
            if callable(path):
                path = path()
        except VariableDoesNotExist:
            msg = ("{% get_metadata %} needs a RequestContext with the "
                  "'django.core.context_processors.request' context processor.")
            logging.warning(msg) # or is this an error?
            return ""

        kwargs = {}

        # If a site is given, pass that on
        if self.site:
            kwargs['site'] = self.site.resolve(context)

        # If a language is given, pass that on
        if self.language:
            kwargs['language'] = self.language.resolve(context)

        # Fetch the meta data
        meta_data = get_meta_data(path, self.meta_data_name, context, **kwargs)

        # If a variable name is given, store the result there
        if self.variable_name is not None:
            context[self.variable_name] = meta_data
            return ""
        else:
            return unicode(meta_data)


def do_get_metadata(parser, token):
    """
    Retrieve an object which can produce (and format) meta data.

        {% get_metadata [for my_path] [in my_language] [on my_site] [as my_variable] %}

        or if you have multiple meta data classes:

        {% get_metadata MyClass [as my_variable] %}

    """
    bits = list(token.split_contents())
    tag_name = bits[0]
    bits = bits[1:]
    meta_data_name = None
    args = { 'as': None, 'for': None, 'in': None, 'on': None }

    if len(bits) % 2:
        meta_data_name = bits[0]
        bits = bits[1:]
    while len(bits):
        if len(bits) < 2 or bits[0] not in args:
            raise template.TemplateSyntaxError("expected format is '%r [as <variable_name>]'" % tag_name)
        args[bits[0]] = bits[1]
        bits = bits[2:]

    return MetaDataNode(meta_data_name, args['as'], args['for'], args['on'], args['in'])


register.tag('get_metadata', do_get_metadata)

