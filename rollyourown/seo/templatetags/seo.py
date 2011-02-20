#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django import template
from rollyourown.seo import get_metadata, get_linked_metadata
from django.template import VariableDoesNotExist

register = template.Library()

class MetadataNode(template.Node):
    def __init__(self, metadata_name, variable_name, target, site, language):
        self.metadata_name = metadata_name
        self.variable_name = variable_name
        self.target = template.Variable(target or 'request.path')
        self.site = site and template.Variable(site) or None
        self.language = language and template.Variable(language) or None

    def render(self, context):
        try:
            target = self.target.resolve(context)
        except VariableDoesNotExist:
            msg = (u"{% get_metadata %} needs some path information.\n"
                        u"Please use RequestContext with the django.core.context_processors.request context processor.\n"
                        "Or provide a path or object explicitly, eg {% get_metadata for path %} or {% get_metadata for object %}")
            raise template.TemplateSyntaxError(msg)
        else:
            if callable(target):
                target = target()
            if isinstance(target, basestring):
                path = target
            elif hasattr(target, 'get_absolute_url'):
                path = target.get_absolute_url()
            elif hasattr(target, "__iter__") and 'get_absolute_url' in target:
                path = target['get_absolute_url']()
            else:
                path = None

        kwargs = {}

        # If a site is given, pass that on
        if self.site:
            kwargs['site'] = self.site.resolve(context)

        # If a language is given, pass that on
        if self.language:
            kwargs['language'] = self.language.resolve(context)

        metadata = None
        # If the target is a django model object
        if hasattr(target, 'pk'):
            metadata = get_linked_metadata(target, self.metadata_name, context, **kwargs)
        if not isinstance(path, basestring):
            path = None
        if not metadata:
            # Fetch the metadata
            try:
                metadata = get_metadata(path, self.metadata_name, context, **kwargs)
            except Exception, e:
                raise template.TemplateSyntaxError(e)

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

        {% get_metadata MyClass [for my_path] [in my_language] [on my_site] [as my_variable] %}

    """
    bits = list(token.split_contents())
    tag_name = bits[0]
    bits = bits[1:]
    metadata_name = None
    args = { 'as': None, 'for': None, 'in': None, 'on': None }

    # If there are an even number of bits, 
    # a metadata name has been provided.
    if len(bits) % 2:
        metadata_name = bits[0]
        bits = bits[1:]

    # Each bits are in the form "key value key value ..."
    # Valid keys are given in the 'args' dict above.
    while len(bits):
        if len(bits) < 2 or bits[0] not in args:
            raise template.TemplateSyntaxError("expected format is '%r [as <variable_name>]'" % tag_name)
        key, value, bits = bits[0], bits[1], bits[2:]
        args[key] = value

    return MetadataNode(metadata_name, 
                variable_name = args['as'], 
                target = args['for'], 
                site = args['on'], 
                language = args['in'])


register.tag('get_metadata', do_get_metadata)

