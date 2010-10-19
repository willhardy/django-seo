# -*- coding: UTF-8 -*-

from django import forms
from django.utils.html import strip_tags

class RawHeadField(forms.TextField):
    """ Form field for a seo.Raw() field, appearing in the head. """
    def clean(self, value):
        if strip_tags(value).strip():
            raise forms.ValidationError("Extra code may not contain text outside tags (advanced use only).")
        return value
