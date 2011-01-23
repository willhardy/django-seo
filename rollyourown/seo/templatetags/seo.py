#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django import template
from rollyourown.seo import get_metadata, get_linked_metadata
from django.template import VariableDoesNotExist

register = template.Library()

class MetadataNode(template.Node):
    def __init__(self, metadata_name, variable_name, path, site, language):
        self.metadata_name = metadata_name
        self.variable_name = variable_name
        self.path = template.Variable(path or 'request.META.PATH_INFO')
        self.site = site and template.Variable(site) or None
        self.language = language and template.Variable(language) or None

    def render(self, context):
        try:
            path = self.path.resolve(context)
            if hasattr(path, 'get_absolute_url'):
                path = path.get_absolute_url
            if hasattr(path, "__iter__") and 'get_absolute_url' in path:
                path = path['get_absolute_url']
            if callable(path):
                path = path()
        except VariableDoesNotExist:
            msg = (u"{% get_metadata %} needs some path information.\n"
                        u"Please use RequestContext with the django.core.context_processors.request context processor.\n"
                        "Or provide a path or object explicitly, eg {% get_metadata for path %} or {% get_metadata for object %}")
            raise template.TemplateSyntaxError(msg)

        kwargs = {}

        # If a site is given, pass that on
        if self.site:
            kwargs['site'] = self.site.resolve(context)

        # If a language is given, pass that on
        if self.language:
            kwargs['language'] = self.language.resolve(context)

        metadata = None
        # If the path is a djano model object
        if hasattr(path, 'pk'):
            metadata = get_linked_metadata(path, self.metadata_name, context, **kwargs)
        if not isinstance(path, basestring):
            path = None
        if not metadata:
            # Fetch the metadata
            metadata = get_metadata(path, self.metadata_name, context, **kwargs)

        # If a variable name is given, store the result there
        if self.variable_name is not None:
            context[self.variable_name] = metadata
            return ""
        else:
            return unicode(metadata)


def do_get_metadata(parser, token):
    """
    Retrieve an object which can produce (and format) metadata.

        {% get_metadata [for my_path] [in my_language] [on my_site] [as my_variable] %}

        or if you have multiple metadata classes:

        {% get_metadata MyClass [as my_variable] %}

    """
    bits = list(token.split_contents())
    tag_name = bits[0]
    bits = bits[1:]
    metadata_name = None
    args = { 'as': None, 'for': None, 'in': None, 'on': None }

    if len(bits) % 2:
        metadata_name = bits[0]
        bits = bits[1:]
    while len(bits):
        if len(bits) < 2 or bits[0] not in args:
            raise template.TemplateSyntaxError("expected format is '%r [as <variable_name>]'" % tag_name)
        args[bits[0]] = bits[1]
        bits = bits[2:]

    return MetadataNode(metadata_name, args['as'], args['for'], args['on'], args['in'])


register.tag('get_metadata', do_get_metadata)

