# -*- coding: utf-8 -*-

# TODO:
#    * Move/rename namespace polluting attributes
#    * Documentation
#    * Make backends optional: Meta.backends = (path, modelinstance/model, view)

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from django.utils.functional import curry
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils.safestring import mark_safe
from django.core.cache import cache
from django.utils.hashcompat import md5_constructor
from django.utils.encoding import iri_to_uri

from rollyourown.seo.utils import NotSet, Literal
from rollyourown.seo.options import Options
from rollyourown.seo.fields import MetadataField, Tag, MetaTag, KeywordTag, Raw
from rollyourown.seo.backends import backend_registry, RESERVED_FIELD_NAMES


registry = SortedDict()


class FormattedMetadata(object):
    """ Allows convenient access to selected metadata.
        Metadata for each field may be sourced from any one of the relevant instances passed.
    """

    def __init__(self, metadata, instances, path, site=None, language=None):
        self.__metadata = metadata
        if metadata._meta.use_cache:
            if metadata._meta.use_sites and site:
                hexpath = md5_constructor(iri_to_uri(site.domain+path)).hexdigest() 
            else:
                hexpath = md5_constructor(iri_to_uri(path)).hexdigest() 
            if metadata._meta.use_i18n:
                self.__cache_prefix = 'rollyourown.seo.%s.%s.%s' % (self.__metadata.__class__.__name__, hexpath, language)
            else:
                self.__cache_prefix = 'rollyourown.seo.%s.%s' % (self.__metadata.__class__.__name__, hexpath)
        else:
            self.__cache_prefix = None
        self.__instances_original = instances
        self.__instances_cache = []

    def __instances(self):
        """ Cache instances, allowing generators to be used and reused. 
            This fills a cache as the generator gets emptied, eventually
            reading exclusively from the cache.
        """
        for instance in self.__instances_cache:
            yield instance
        for instance in self.__instances_original:
            self.__instances_cache.append(instance)
            yield instance

    def _resolve_value(self, name):
        """ Returns an appropriate value for the given name. 
            This simply asks each of the instances for a value.
        """
        for instance in self.__instances():
            value = instance._resolve_value(name)
            if value:
                return value

        # Otherwise, return an appropriate default value (populate_from)
        # TODO: This is duplicated in meta_models. Move this to a common home.
        if name in self.__metadata._meta.elements:
            populate_from = self.__metadata._meta.elements[name].populate_from
            if callable(populate_from):
                return populate_from(None)
            elif isinstance(populate_from, Literal):
                return populate_from.value
            elif populate_from is not NotSet:
                return self._resolve_value(populate_from)

    def __getattr__(self, name):
        # If caching is enabled, work out a key
        if self.__cache_prefix:
            cache_key = '%s.%s' % (self.__cache_prefix, name)
            value = cache.get(cache_key)
        else:
            cache_key = None
            value = None

        # Look for a group called "name"
        if name in self.__metadata._meta.groups:
            if value is not None:
                return value or None
            value = '\n'.join(unicode(BoundMetadataField(self.__metadata._meta.elements[f], self._resolve_value(f))) for f in self.__metadata._meta.groups[name]).strip()

        # Look for an element called "name"
        elif name in self.__metadata._meta.elements:
            if value is not None:
                return BoundMetadataField(self.__metadata._meta.elements[name], value or None)
            value = self._resolve_value(name)
            if cache_key is not None:
                cache.set(cache_key, value or '')
            return BoundMetadataField(self.__metadata._meta.elements[name], value)
        else:
            raise AttributeError

        if cache_key is not None:
            cache.set(cache_key, value or '')

        return value or None

    def __unicode__(self):
        """ String version of this object is the html output of head elements. """
        if self.__cache_prefix is not None:
            value = cache.get(self.__cache_prefix)
        else:
            value = None

        if value is None:
            value = mark_safe(u'\n'.join(unicode(getattr(self, f)) for f,e in self.__metadata._meta.elements.items() if e.head))
            if self.__cache_prefix is not None:
                cache.set(self.__cache_prefix, value or '')

        return value


class BoundMetadataField(object):
    """ An object to help provide templates with access to a "bound" metadata field. """

    def __init__(self, field, value):
        self.field = field
        if value:
            self.value = field.clean(value)
        else:
            self.value = None

    def __unicode__(self):
        if self.value:
            return mark_safe(self.field.render(self.value))
        else:
            return u""

    def __str__(self):
        return self.__unicode__().encode("ascii", "ignore")


class MetadataBase(type):
    def __new__(cls, name, bases, attrs):
        # TODO: Think of a better test to avoid processing Metadata parent class
        if bases == (object,):
            return type.__new__(cls, name, bases, attrs)

        # Save options as a dict for now (we will be editing them)
        # TODO: Is this necessary, should we bother relaying Django Meta options?
        Meta = attrs.pop('Meta', {})
        if Meta:
            Meta = Meta.__dict__.copy()

        # Remove our options from Meta, so Django won't complain
        help_text = attrs.pop('HelpText', {})

        # TODO: Is this necessary
        if help_text:
            help_text = help_text.__dict__.copy()

        options = Options(Meta, help_text)

        # Collect and sort our elements
        elements = [(key, attrs.pop(key)) for key, obj in attrs.items() 
                                        if isinstance(obj, MetadataField)]
        elements.sort(lambda x, y: cmp(x[1].creation_counter, 
                                                y[1].creation_counter))
        elements = SortedDict(elements)

        # Validation:
        # TODO: Write a test framework for seo.Metadata validation
        # Check that no group names clash with element names
        for key,members in options.groups.items():
            assert key not in elements, "Group name '%s' clashes with field name" % key
            for member in members:
                assert member in elements, "Group member '%s' is not a valid field" % member

        # Check that the names of the elements are not going to clash with a model field
        for key in elements:
            assert key not in RESERVED_FIELD_NAMES, "Field name '%s' is not allowed" % key


        # Preprocessing complete, here is the new class
        new_class = type.__new__(cls, name, bases, attrs)

        options.metadata = new_class
        new_class._meta = options

        # Some useful attributes
        options._update_from_name(name)
        options._register_elements(elements)

        try:
            for backend_name in options.backends:
                new_class._meta._add_backend(backend_registry[backend_name])
            for backend_name in options.backends:
                backend_registry[backend_name].validate(options)
        except KeyError:
            raise Exception('Metadata backend "%s" is not installed.' % backend_name)

        #new_class._meta._add_backend(PathBackend)
        #new_class._meta._add_backend(ModelInstanceBackend)
        #new_class._meta._add_backend(ModelBackend)
        #new_class._meta._add_backend(ViewBackend)

        registry[name] = new_class

        return new_class


    # TODO: Move this function out of the way (subclasses will want to define their own attributes)
    def _get_formatted_data(cls, path, context=None, site=None, language=None):
        """ Return an object to conveniently access the appropriate values. """
        return FormattedMetadata(cls(), cls._get_instances(path, context, site, language), path, site, language)


    # TODO: Move this function out of the way (subclasses will want to define their own attributes)
    def _get_instances(cls, path, context=None, site=None, language=None):
        """ A sequence of instances to discover metadata. 
            Each instance from each backend is looked up when possible/necessary.
            This is a generator to eliminate unnecessary queries.
        """
        backend_context = {'view_context': context }

        for model in cls._meta.models.values():
            for instance in model.objects.get_instances(path, site, language, backend_context) or []:
                if hasattr(instance, '_process_context'):
                    instance._process_context(backend_context)
                yield instance


class Metadata(object):
    __metaclass__ = MetadataBase


def _get_metadata_model(name=None):
    # Find registered Metadata object
    if name is not None:
        try:
            return registry[name]
        except KeyError:
            if len(registry) == 1:
                valid_names = u'Try using the name "%s" or simply leaving it out altogether.'% registry.keys()[0]
            else:
                valid_names = u"Valid names are " + u", ".join(u'"%s"' % k for k in registry.keys())
            raise Exception(u"Metadata definition with name \"%s\" does not exist.\n%s" % (name, valid_names))
    else:
        assert len(registry) == 1, "You must have exactly one Metadata class, if using get_metadata() without a 'name' parameter."
        return registry.values()[0]


def get_metadata(path, name=None, context=None, site=None, language=None):
    metadata = _get_metadata_model(name)
    return metadata._get_formatted_data(path, context, site, language)


def get_linked_metadata(obj, name=None, context=None, site=None, language=None):
    """ Gets metadata linked from the given object. """
    # XXX Check that 'modelinstance' and 'model' metadata are installed in backends
    # I believe that get_model() would return None if not
    Metadata = _get_metadata_model(name)
    InstanceMetadata = Metadata._meta.get_model('modelinstance')
    ModelMetadata = Metadata._meta.get_model('model')
    content_type = ContentType.objects.get_for_model(obj)
    instances = []
    if InstanceMetadata is not None:
        try:
            instance_md = InstanceMetadata.objects.get(_content_type=content_type, _object_id=obj.pk)
        except InstanceMetadata.DoesNotExist:
            instance_md = InstanceMetadata(_content_object=obj)
        instances.append(instance_md)
    if ModelMetadata is not None:
        try:
            model_md = ModelMetadata.objects.get(_content_type=content_type)
        except ModelMetadata.DoesNotExist:
            model_md = ModelMetadata(_content_type=content_type)
        instances.append(model_md)    
    return FormattedMetadata(Metadata, instances, '', site, language)


def create_metadata_instance(metadata_class, instance):
    # If this instance is marked as handled, don't do anything
    # This typically means that the django admin will add metadata 
    # using eg an inline.
    if getattr(instance, '_MetadataFormset__seo_metadata_handled', False):
        return

    metadata = None
    content_type = ContentType.objects.get_for_model(instance)
    
    # If this object does not define a path, don't worry about automatic update
    try:
        path = instance.get_absolute_url()
    except AttributeError:
        return

    # Look for an existing object with this path
    language = getattr(instance, '_language', None)
    site = getattr(instance, '_site', None)
    for md in metadata_class.objects.get_instances(path, site, language):
        # If another object has the same path, remove the path.
        # It's harsh, but we need a unique path and will assume the other
        # link is outdated.
        if md._content_type != content_type or md._object_id != instance.pk:
            md._path = md._content_object.get_absolute_url()
            md.save()
            # Move on, this metadata instance isn't for us
            md = None
        else:
            # This is our instance!
            metadata = md
    
    # If the path-based search didn't work, look for (or create) an existing
    # instance linked to this object.
    if not metadata:
        metadata, md_created = metadata_class.objects.get_or_create(_content_type=content_type, _object_id=instance.pk)
        metadata._path = path
        metadata.save()


def populate_metadata(model, MetadataClass):
    """ For a given model and metadata class, ensure there is metadata for every instance. 
    """
    content_type = ContentType.objects.get_for_model(model)
    for instance in model.objects.all():
        create_metadata_instance(MetadataClass, instance)


def _update_callback(model_class, sender, instance, created, **kwargs):
    """ Callback to be attached to a post_save signal, updating the relevant
        metadata, or just creating an entry. 
    
        NB:
        It is theoretically possible that this code will lead to two instances
        with the same generic foreign key.  If you have non-overlapping URLs,
        then this shouldn't happen.
        I've held it to be more important to avoid double path entries.
    """
    create_metadata_instance(model_class, instance)


def _delete_callback(model_class, sender, instance,  **kwargs):
    content_type = ContentType.objects.get_for_model(instance)
    model_class.objects.filter(_content_type=content_type, _object_id=instance.pk).delete()


def register_signals():
    for metadata_class in registry.values():
        model_instance = metadata_class._meta.get_model('modelinstance')
        if model_instance is not None:
            update_callback = curry(_update_callback, model_class=model_instance)
            delete_callback = curry(_delete_callback, model_class=model_instance)

            ## Connect the models listed in settings to the update callback.
            for model in metadata_class._meta.seo_models:
                models.signals.post_save.connect(update_callback, sender=model, weak=False)
                models.signals.pre_delete.connect(delete_callback, sender=model, weak=False)


