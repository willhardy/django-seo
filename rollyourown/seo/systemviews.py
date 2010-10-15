#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from rollyourown.seo.utils import LazyChoices
from django.utils.functional import lazy

class SystemViews(LazyChoices):
    def populate(self):
        """ Populate this list with all views that take no arguments.
        """
        from django.conf import settings
        from django.core import urlresolvers

        self.append(("", ""))
        urlconf = settings.ROOT_URLCONF
        resolver = urlresolvers.RegexURLResolver(r'^/', urlconf)
        # Collect base level views
        for key, value in resolver.reverse_dict.items():
            if isinstance(key, basestring):
                args = value[0][0][1]
                url = "/" + value[0][0][0]
                self.append((key, " ".join(key.split("_"))))
        # Collect namespaces (TODO: merge these two sections into one)
        for namespace, url in resolver.namespace_dict.items():
            for key, value in url[1].reverse_dict.items():
                if isinstance(key, basestring):
                    args = value[0][0][1]
                    full_key = '%s:%s' % (namespace, key)
                    self.append((full_key, "%s: %s" % (namespace, " ".join(key.split("_")))))
        self.sort()


from django import forms
class SystemViewChoiceField(forms.TypedChoiceField):
    def _get_choices(self):
        return self._choices
    def _set_choices(self, value):
        self._choices =  self.widget.choices = value
    choices = property(_get_choices, _set_choices)


from django.db.models.fields import BLANK_CHOICE_DASH
from django.db import models
from django.utils.text import capfirst
class SystemViewField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 255)
        kwargs.setdefault('choices', SystemViews())
        super(SystemViewField, self).__init__(*args, **kwargs)

    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH):
        return self.choices

    def formfield(self, **kwargs):
        defaults = {'required': not self.blank, 'label': capfirst(self.verbose_name), 'help_text': self.help_text}
        if self.has_default():
            if callable(self.default):
                defaults['initial'] = self.default
                defaults['show_hidden_initial'] = True
            else:
                defaults['initial'] = self.get_default()
        include_blank = self.blank or not (self.has_default() or 'initial' in kwargs)
        defaults['choices'] = self.get_choices(include_blank=include_blank)
        defaults['coerce'] = self.to_python
        if self.null:
            defaults['empty_value'] = None
        form_class = SystemViewChoiceField
        # Many of the subclass-specific formfield arguments (min_value,
        # max_value) don't apply for choice fields, so be sure to only pass
        # the values that TypedChoiceField will understand.
        for k in kwargs.keys():
            if k not in ('coerce', 'empty_value', 'choices', 'required',
                         'widget', 'label', 'initial', 'help_text',
                         'error_messages', 'show_hidden_initial'):
                del kwargs[k]
        defaults.update(kwargs)
        return form_class(**defaults)


# help south understand our models
try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^seo\.fields"])
except ImportError:
    pass
