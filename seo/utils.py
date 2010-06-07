# -*- coding: utf-8 -*-

import logging
from django.conf import settings
from django.db import models

setting_name_seo_models = "SEO_MODELS"

def get_seo_models():
    """ Returns a list of models that are defined in settings (SEO_MODELS)
    """
    seo_models = []
    for model_name in getattr(settings, setting_name_seo_models, ()):
        if "." in model_name:
            # TODO: Test this block
            app_label, model_name = model_name.split(".", 1)
            model = models.get_model(app_label, model_name)
            if model:
                seo_models.append(model)
        else:
            app = models.get_app(model_name)
            if app:
                seo_models.extend(models.get_models(app))

    return seo_models


def get_seo_content_types():
    """ Returns a list of content types from the models defined in settings (SEO_MODELS) """
    # TODO: Test this function
    from django.contrib.contenttypes.models import ContentType
    logging.debug("Populating content type choices.")
    return [ ContentType.objects.get_for_model(m) for m in get_seo_models() ]


class LazyList(list):
    """ Generic python list which is populated when items are first accessed.
    """

    def populate(self):
        """ Populates the list.
            This method must be overridden by subclasses.
            It is called once, when items in the list are first accessed.
        """
        raise NotImplementedError

    # Ensure list is only populated once
    def __init__(self, populate_function=None):
        if populate_function is not None:
            # TODO: Test this functionality!
            self.populate = populate_function
        self._populated = False
    def _populate(self):
        """ Populate this list by calling populate(), but only once. """
        if not self._populated:
            logging.debug("Populating lazy list %d (%s)" % (id(self), self.__class__.__name__))
            self.populate()
            self._populated = True

    # Accessing methods that require a populated field
    def __len__(self):
        self._populate()
        return super(LazyList, self).__len__()
    def __getitem__(self, key):
        self._populate()
        return super(LazyList, self).__getitem__(key)
    def __setitem__(self, key, value):
        self._populate()
        return super(LazyList, self).__setitem__(key, value)
    def __delitem__(self, key):
        self._populate()
        return super(LazyList, self).__delitem__(key)
    def __iter__(self):
        self._populate()
        return super(LazyList, self).__iter__()
    def __contains__(self, item):
        self._populate()
        return super(LazyList, self).__contains__(item)


class LazyChoices(LazyList):
    """ Allows a choices list to be given to Django model fields which is
        populated after the models have been defined (ie on validation).
    """

    def __nonzero__(self):
        # Django tests for existence too early, meaning population is attempted
        # before the models have been imported. 
        # This may have some side effects if truth testing is supposed to
        # evaluate the list, but in the case of django choices, this is not
        # The case. This prevents __len__ from being called on truth tests.
        if not self._populated:
            return True
        else:
            return bool(len(self))


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


class SEO_CONTENT_TYPE_CHOICES(dict):
    """ Class to lazily populate the choices for content types (they wont be there before a syncdb). 
        Items are populated on first interaction (getattr or len) with dict.

        TODO: Test this class
    """
    def _populate_content_types(self):
        if not super(SEO_CONTENT_TYPE_CHOICES, self).__len__():
            self['id__in'] = [ct.id for ct in get_seo_content_types()]

    def __getitem__(self, key):
        self._populate_content_types()
        return super(SEO_CONTENT_TYPE_CHOICES, self).__getitem__(key)

    def __len__(self):
        self._populate_content_types()
        return super(SEO_CONTENT_TYPE_CHOICES, self).__len__()

    def __iter__(self):
        self._populate_content_types()
        return super(SEO_CONTENT_TYPE_CHOICES, self).__iter__()

SEO_CONTENT_TYPE_CHOICES = SEO_CONTENT_TYPE_CHOICES()



from django.core.urlresolvers import RegexURLResolver, RegexURLPattern, Resolver404, get_resolver

def _pattern_resolve_to_name(pattern, path):
    match = pattern.regex.search(path)
    if match:
        name = ""
        if pattern.name:
            name = pattern.name
        elif hasattr(pattern, '_callback_str'):
            name = pattern._callback_str
        else:
            name = "%s.%s" % (pattern.callback.__module__, pattern.callback.func_name)
        return name

def _resolver_resolve_to_name(resolver, path):
    tried = []
    match = resolver.regex.search(path)
    if match:
        new_path = path[match.end():]
        for pattern in resolver.url_patterns:
            try:
                if isinstance(pattern, RegexURLPattern):
                    name = _pattern_resolve_to_name(pattern, new_path)
                elif isinstance(pattern, RegexURLResolver):
                    name = _resolver_resolve_to_name(pattern, new_path)
            except Resolver404, e:
                tried.extend([(pattern.regex.pattern + '   ' + t) for t in e.args[0]['tried']])
            else:
                if name:
                    return name
                tried.append(pattern.regex.pattern)
        raise Resolver404, {'tried': tried, 'path': new_path}

def resolve_to_name(path, urlconf=None):
    return _resolver_resolve_to_name(get_resolver(urlconf), path)


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
