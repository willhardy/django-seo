# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.db import models
from django.utils.functional import lazy


class NotSet(object):
    " A singleton to identify unset values (where None would have meaning) "
    def __str__(self): return "NotSet"
    def __repr__(self): return self.__str__()
NotSet = NotSet()


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
    try:
        return _resolver_resolve_to_name(get_resolver(urlconf), path)
    except Resolver404:
        return None

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# XXX: Replace with escape_tags
def strip_tags(value, valid_tags):
    """ Strips text from the given html string, leaving only tags.
        This functionality requires BeautifulSoup, nothing will be 
        done otherwise.
    """
    # TODO Test that tags inside eg <meta> tags or scripts are left alone
    if BeautifulSoup is None:
        return value
    soup = BeautifulSoup(value)
    [ tag.extract() for tag in list(soup) if not (getattr(tag, 'name', None) in valid_tags) ]
    return str(soup)

def escape_tags(value, valid_tags):
    """ Strips text from the given html string, leaving only tags.
        This functionality requires BeautifulSoup, nothing will be 
        done otherwise.
    """
    # TODO Test that tags inside eg <meta> tags or scripts are left alone
    if BeautifulSoup is None:
        return value
    soup = BeautifulSoup(value)
    [ tag.extract() for tag in list(soup) if not (getattr(tag, 'name', None) in valid_tags) ]
    return str(soup)
