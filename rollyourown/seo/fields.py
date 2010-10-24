#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.html import conditional_escape

from rollyourown.seo.utils import escape_tags, NotSet, Literal


VALID_HEAD_TAGS = "head title base link meta script".split()
VALID_INLINE_TAGS = (
    "area img object map param "
    "a abbr acronym dfn em strong "
    "code samp kbd var "
    "b i big small tt " # would like to leave these out :-)
    "span br bdo cite del ins q sub sup"
    # NB: deliberately leaving out iframe and script
).split()


class MetaDataField(object):
    creation_counter = 0

    # TODO: verbose_name, max_length
    def __init__(self, name, head, editable, populate_from, valid_tags, choices, help_text, field, field_kwargs):
        self.name = name
        self.head = head
        self.editable = editable
        self.populate_from = populate_from
        self.help_text = help_text
        self.field = field or models.CharField
        if field_kwargs is None: field_kwargs = {}
        self.field_kwargs = field_kwargs

        if choices and isinstance(choices[0], basestring):
            choices = [(c, c) for c in choices]
        field_kwargs.setdefault('choices', choices)

        # If valid_tags is a string, tags are space separated words
        if isinstance(valid_tags, basestring):
            valid_tags = valid_tags.split()
        if valid_tags is not None:
            valid_tags = set(valid_tags)
        self.valid_tags = valid_tags


        # Track creation order for field ordering
        self.creation_counter = MetaDataField.creation_counter
        MetaDataField.creation_counter += 1

    def contribute_to_class(self, cls, name):
        if not self.name:
            self.name = name
        # Populate the hep text from populate_from if it's missing
        if not self.help_text and self.populate_from is not NotSet:
            if callable(self.populate_from) and hasattr(self.populate_from, 'short_description'):
                self.help_text = _('If empty, %s') % self.populate_from.short_description
            elif isinstance(self.populate_from, Literal):
                self.help_text = _('If empty, \"%s\" will be used.') % self.populate_from.value
            elif isinstance(self.populate_from, basestring) and self.populate_from in cls.elements:
                self.help_text = _('If empty, %s will be used.') % self.populate_from
            elif isinstance(self.populate_from, basestring) and hasattr(cls, self.populate_from): 
                populate_from = getattr(cls, self.populate_from, None)
                if callable(populate_from) and hasattr(populate_from, 'short_description'):
                    self.help_text = _('If empty, %s') % populate_from.short_description
        self.validate()

    def validate(self):
        """ Discover certain illegal configurations """
        if not self.editable:
            assert self.populate_from is not NotSet, u"If field (%s) is not editable, you must set populate_from" % self.name

    def get_field(self):
        kwargs = self.field_kwargs
        if self.help_text:
            kwargs.setdefault('help_text', self.help_text)
        return self.field(**kwargs)

    def clean(self, value):
        return value

    def render(self, value):
        raise NotImplementedError


class Tag(MetaDataField):
    def __init__(self, name=None, head=False, escape_value=True,
                       editable=True, verbose_name=None, valid_tags=None, max_length=511,
                       choices=None, populate_from=NotSet, field=models.CharField, 
                       field_kwargs=None, help_text=None):

        self.escape_value = escape_value
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('verbose_name', verbose_name)
        field_kwargs.setdefault('max_length', max_length)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)
        super(Tag, self).__init__(name, head, editable, populate_from, valid_tags, choices, help_text, field, field_kwargs)

    def clean(self, value):
        value = escape_tags(value, self.valid_tags or VALID_INLINE_TAGS)

        return value.strip()

    def render(self, value):
        return u'<%s>%s</%s>' % (self.name, value, self.name)


VALID_META_NAME = re.compile(r"[A-z][A-z0-9_:.-]*$")

class MetaTag(MetaDataField):
    def __init__(self, name=None, head=True, verbose_name=None, editable=True, 
                       populate_from=NotSet, valid_tags=None, max_length=511, choices=None, 
                       field=models.CharField, field_kwargs=None, help_text=None):
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('verbose_name', verbose_name)
        field_kwargs.setdefault('max_length', max_length)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)

        if name is not None:
            assert VALID_META_NAME.match(name) is not None, u"Invalid name for MetaTag: '%s'" % name

        super(MetaTag, self).__init__(name, head, editable, populate_from, valid_tags, choices, help_text, field, field_kwargs)

    def clean(self, value):
        value = escape_tags(value, self.valid_tags)

        # Replace newlines with spaces
        return value.replace("\n", " ").strip()

    def render(self, value):
        # TODO: HTML/XHTML?
        return u'<meta name="%s" content="%s" />' % (self.name, value)

class KeywordTag(MetaTag):
    def __init__(self, name=None, head=True, verbose_name=None, editable=True, 
                       populate_from=NotSet, valid_tags=None, max_length=511, choices=None,
                       field=models.CharField, field_kwargs=None, help_text=None):
        if name is None:
            name = "keywords"
        if valid_tags is None:
            valid_tags = []
        super(KeywordTag, self).__init__(name, head, verbose_name, editable, 
                        populate_from, valid_tags, max_length, choices, field, 
                        field_kwargs, help_text)

    def clean(self, value):
        value = escape_tags(value, self.valid_tags)

        # Remove double quote, replace newlines with commas
        return value.replace('"', '&#34;').replace("\n", ", ").strip()


# TODO: if max_length is given, use a CharField and pass it through
class Raw(MetaDataField):
    def __init__(self, head=True, editable=True, populate_from=NotSet, 
                    verbose_name=None, valid_tags=None, choices=None, field=models.TextField,
                    field_kwargs=None, help_text=None):
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('verbose_name', verbose_name)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)
        super(Raw, self).__init__(None, head, editable, populate_from, valid_tags, choices, help_text, field, field_kwargs)

    def clean(self, value):
        # Find a suitable set of valid tags using self.head and self.valid_tags
        if self.head:
            valid_tags = set(VALID_HEAD_TAGS)
            if self.valid_tags is not None:
                valid_tags = valid_tags & self.valid_tags
        else:
            valid_tags = self.valid_tags

        value = escape_tags(value, valid_tags)

        if self.head:
            # Remove text before tags
            before_tags = re.compile("^([^<>]*)<")
            value = before_tags.sub('<', value)

            # Remove text after tags
            after_tags = re.compile(">([^<>]*)$")
            value = after_tags.sub('>', value)

        return value

    def render(self, value):
        return value


