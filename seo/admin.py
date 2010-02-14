# -*- coding: UTF-8 -*-

from django.contrib import admin
from django.contrib.contenttypes import generic
from seo import models

from django import forms
from django.utils.html import strip_tags


class MetaDataForm(forms.ModelForm):
    class Meta:
        model = models.MetaData

    def clean_extra(self):
        value = self.cleaned_data['extra']
        # Reject if text is found outside tags, as extra will appear in <head>
        if strip_tags(value).strip():
            raise forms.ValidationError("Extra code may not contain text outside tags (advanced use only).")
        return value


class InlineMetaDataForm(forms.ModelForm):
    class Meta:
        model = models.MetaData
        fields = ('title', 'heading', 'subheading', 'keywords', 'description' )

    #def save(self, commit=True):
        #super(InlineMetaDataForm, self).save(commit)


class MetaDataInline(generic.GenericStackedInline):
    """ Inline for inclusion in any relatable model admin. 
        Simply import and add to the list of inlines.
    """
    max_num = 1
    model = models.MetaData
    form = InlineMetaDataForm


class MetaDataAdmin(admin.ModelAdmin):
    list_display = ('path', 'title', 'heading', 'subheading', 'content_type', )#'keywords', 'description', 'content_type')
    list_editable = ('title', 'heading', 'subheading')#'keywords', 'description')
    list_filter = ('content_type',)
    search_fields = ('path', 'title', 'keywords', 'description', 'heading', 'subheading')
    fieldsets = (
        (None, {
            'fields': ('path', 'title', 'keywords', 'description', 'heading', 'subheading')
        }),
        ('Advanced', {
            'classes' : ('collapse',),
            'fields': ('extra', )
        }),
        )

admin.site.register(models.MetaData, MetaDataAdmin)
