#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from django.utils.functional import lazy
from django.db.utils import DatabaseError

def _get_seo_content_types(seo_models):
    """ Returns a list of content types from the models defined in settings (SEO_MODELS) """
    try:
        from django.contrib.contenttypes.models import ContentType
        return [ ContentType.objects.get_for_model(m).id for m in seo_models ]
    except DatabaseError:
        # Return an empty list if this is called too early
        return []
def get_seo_content_types(seo_models):
    return lazy(_get_seo_content_types, list)(seo_models)


from django import forms
class SEOModelChoiceField(forms.ModelChoiceField):
    def _get_choices(self):
        return self._choices
    def _set_choices(self, value):
        self._choices = self.widget.choices = value
    choices = property(_get_choices, _set_choices)

from django.db.models.fields import BLANK_CHOICE_DASH
from django.db import models
from django.utils.text import capfirst
class SEOContentTypeField(models.ForeignKey):

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
