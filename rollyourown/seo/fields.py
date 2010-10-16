#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape

from rollyourown.seo.utils import strip_tags, NotSet


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

    def __init__(self, name, head, editable, populate_from, valid_tags, field, field_kwargs):
        self.name = name
        self.head = head
        self.editable = editable
        self.populate_from = populate_from
        # If valid_tags is a string, tags are space separated words
        if isinstance(valid_tags, basestring):
            valid_tags = valid_tags.split()
        self.valid_tags = set(valid_tags)
        self.field = field or models.CharField

        if field_kwargs is None: field_kwargs = {}
        self.field_kwargs = field_kwargs

        # Track creation order for field ordering
        self.creation_counter = MetaDataField.creation_counter
        MetaDataField.creation_counter += 1

    def contribute_to_class(self, cls, name):
        if not self.name:
            self.name = name
        self.validate()

    def validate(self):
        """ Discover certain illegal configurations """
        if not self.editable:
            assert self.populate_from is not NotSet, u"If field (%s) is not editable, you must set populate_from" % self.name

    def get_field(self):
        return self.field(**self.field_kwargs)

    def clean(self, value):
        return value

    def render(self, value):
        raise NotImplementedError


class Tag(MetaDataField):
    def __init__(self, name=None, head=False, escape_value=True,
                       editable=True, verbose_name=None, valid_tags=None, max_length=511,
                       populate_from=NotSet, field=models.CharField, 
                       field_kwargs=None, help_text=None):

        self.escape_value = escape_value
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('verbose_name', verbose_name)
        field_kwargs.setdefault('max_length', max_length)
        field_kwargs.setdefault('help_text', None)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)
        super(Tag, self).__init__(name, head, editable, populate_from, valid_tags, field, field_kwargs)

    def clean(self, value):
        if self.escape_value:
            value = conditional_escape(value)
        return mark_safe(value.strip())

    def render(self, value):
        return u'<%s>%s</%s>' % (self.name, value, self.name)


VALID_META_NAME = re.compile(r"[A-z][A-z0-9_:.-]*$")

class MetaTag(MetaDataField):
    def __init__(self, name=None, head=True, verbose_name=None, editable=True, 
                       populate_from=NotSet, valid_tags=None, max_length=511, field=models.CharField,
                       field_kwargs=None, help_text=None):
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('verbose_name', verbose_name)
        field_kwargs.setdefault('max_length', max_length)
        field_kwargs.setdefault('help_text', None)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)

        if name is not None:
            assert VALID_META_NAME.match(name) is not None, u"Invalid name for MetaTag: '%s'" % name

        super(MetaTag, self).__init__(name, head, editable, populate_from, valid_tags, field, field_kwargs)

    def clean(self, value):
        return value.replace('"', '&#34;').replace("\n", " ").strip()

    def render(self, value):
        # TODO: HTML/XHTML?
        return mark_safe(u'<meta name="%s" content="%s" />' % (self.name, value))

class KeywordTag(MetaTag):
    def __init__(self, name=None, head=True, verbose_name=None, editable=True, 
                       populate_from=NotSet, valid_tags=None, max_length=511, field=models.CharField,
                       field_kwargs=None, help_text=None):
        if name is None:
            name = "keywords"
        if valid_tags is None:
            valid_tags = []
        super(KeywordTag, self).__init__(name, head, verbose_name, editable, 
                        populate_from, valid_tags, max_length, field, 
                        field_kwargs, help_text)

    def clean(self, value)
        return value.replace('"', '&#34;').replace("\n", ", ").strip()


class Raw(MetaDataField):
    def __init__(self, head=True, editable=True, populate_from=NotSet, 
                    verbose_name=None, valid_tags=None, field=models.TextField,
                    field_kwargs=None, help_text=None):
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('help_text', None)
        field_kwargs.setdefault('verbose_name', verbose_name)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)
        super(Raw, self).__init__(None, head, editable, populate_from, valid_tags, field, field_kwargs)

    def clean(self, value):
        # TODO: escape/strip all but self.valid_tags
        if self.head:
            value = strip_tags(value, VALID_HEAD_TAGS)
        return mark_safe(value)

    def render(self, value):
        return value


