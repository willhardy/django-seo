# -*- coding: utf-8 -*-

# TODO:
#    * Meta.seo_views to list views or apps that will appear in the list in the admin (like Meta.seo_models)
#    * Move/rename namespace polluting attributes
#    * Documentation
#    * Make backends optional: Meta.backends = (path, modelinstance/model, view)
#    * Make cache optional: Meta.use_cache

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from django.utils.functional import curry
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils.safestring import mark_safe
from django.db.models.options import get_verbose_name
from django.core.cache import cache
from django.utils.hashcompat import md5_constructor
from django.utils.encoding import iri_to_uri

from rollyourown.seo.utils import NotSet, Literal

from rollyourown.seo.fields import MetaDataField
from rollyourown.seo.fields import Tag, MetaTag, KeywordTag, Raw
from rollyourown.seo.meta_models import PathMetaDataBase, ModelMetaDataBase, ModelInstanceMetaDataBase, ViewMetaDataBase
from rollyourown.seo.meta_models import SitePathMetaDataBase, SiteModelMetaDataBase, SiteModelInstanceMetaDataBase, SiteViewMetaDataBase
from rollyourown.seo.meta_models import RESERVED_FIELD_NAMES, _get_seo_models


registry = SortedDict()


class FormattedMetaData(object):
    """ Allows convenient access to selected metadata.
        Metadata for each field may be sourced from any one of the relevant instances passed.
    """

    def __init__(self, metadata, instances, path):
        self.__metadata = metadata
        path = md5_constructor(iri_to_uri(path)).hexdigest() 
        self.__cache_prefix = 'rollyourown.seo.%s.%s' % (self.__metadata.__class__.__name__, path)
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
        if name in self.__metadata.elements:
            populate_from = self.__metadata.elements[name].populate_from
            if callable(populate_from):
                # Instance methods have a 'self' under im_self
                if getattr(populate_from, 'im_self', None):
                    return populate_from()
                else:
                    return populate_from(self.__metadata)
            elif isinstance(populate_from, Literal):
                return populate_from.value
            elif populate_from is not NotSet:
                return self._resolve_value(populate_from)

    def __getattr__(self, name):
        cache_key = '%s.%s' % (self.__cache_prefix, name)
        value = cache.get(cache_key)
        # Look for a group called "name"
        if name in self.__metadata.groups:
            if value is not None:
                return value
            value = '\n'.join(unicode(BoundMetaDataField(self.__metadata.elements[f], self._resolve_value(f))) for f in self.__metadata.groups[name]).strip()
        # Look for an element called "name"
        elif name in self.__metadata.elements:
            if value is not None:
                return BoundMetaDataField(self.__metadata.elements[name], value)
            value = BoundMetaDataField(self.__metadata.elements[name], self._resolve_value(name))
        else:
            raise AttributeError

        cache.set(cache_key, value)
        return value

    def __unicode__(self):
        """ String version of this object is the html output of head elements. """
        value = cache.get(self.__cache_prefix)
        if value is None:
            value = mark_safe(u'\n'.join(unicode(getattr(self, f)) for f,e in self.__metadata.elements.items() if e.head))
            cache.set(self.__cache_prefix, value)
        return value


class BoundMetaDataField(object):
    """ An object to help provide templates with access to a "bound" meta data field. """

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


class MetaDataBase(type):
    def __new__(cls, name, bases, attrs):
        # TODO: Think of a better test to avoid processing MetaData parent class
        if bases == (object,):
            return super(MetaDataBase, cls).__new__(cls, name, bases, attrs)

        # Save options as a dict for now (we will be editing them)
        # TODO: Is this necessary, should we bother relaying Django Meta options?
        Meta = attrs.pop('Meta', {})
        if Meta:
            Meta = Meta.__dict__.copy()

        # Remove our options from Meta, so Django won't complain
        groups = Meta.pop('groups', {})
        use_sites = Meta.pop('use_sites', False)
        seo_models = Meta.pop('seo_models', [])
        help_text = attrs.pop('HelpText', {})
        verbose_name = Meta.pop('verbose_name', None)
        verbose_name_plural = Meta.pop('verbose_name_plural', None)
        if help_text:
            help_text = help_text.__dict__.copy()

        # Collect and sort our elements
        elements = [(key, attrs.pop(key)) for key, obj in attrs.items() 
                                        if isinstance(obj, MetaDataField)]
        elements.sort(lambda x, y: cmp(x[1].creation_counter, 
                                                y[1].creation_counter))
        elements = SortedDict(elements)

        # Validation:
        # TODO: Write a test framework for seo.MetaData validation
        # Check that no group names clash with element names
        for key,members in groups.items():
            assert key not in elements, "Group name '%s' clashes with field name" % key
            for member in members:
                assert member in elements, "Group member '%s' is not a valid field" % member

        # Check that the names of the elements are not going to clash with a model field
        for key in elements:
            assert key not in RESERVED_FIELD_NAMES, "Field name '%s' is not allowed" % key


        # Preprocessing complete, here is the new class
        new_class = super(MetaDataBase, cls).__new__(cls, name, bases, attrs)

        # Some useful attributes
        # TODO: Move these polluting names out of the way (subclasses will want to use their own attributes)
        new_class.seo_models = seo_models
        new_class.elements = elements
        new_class.groups = groups
        new_class.use_sites = use_sites
        new_class.verbose_name = verbose_name or get_verbose_name(name)
        new_class.verbose_name_plural = verbose_name_plural or new_class.verbose_name + 's'

        # TODO: Reorganise? should this happen somewhere else?
        for key, obj in elements.items():
            obj.contribute_to_class(new_class, key)

        # Create the Django Models
        # An abstract base and three real models are created using the fields
        # defined above and additional field for attaching metadata to the 
        # relevant path, model or view

        # Create the common Django fields
        fields = {}
        for key, obj in elements.items():
            if obj.editable:
                field = obj.get_field()
                if not field.help_text:
                    if key in help_text:
                        field.help_text = help_text[key]
                fields[key] = field

        # 0. Abstract base model with common fields
        base_meta = type('Meta', (), Meta)
        class BaseMeta(base_meta):
            abstract = True
            app_label = 'seo'
        fields['Meta'] = BaseMeta
        fields['__module__'] = attrs['__module__']
        MetaDataBaseModel = type('%sBase' % name, (models.Model,), fields)

        # Function to build our subclasses for us
        def create_new_class(md_type, base):
            # TODO: Rename this field
            new_md_attrs = {'_meta_data': new_class, '__module__': __name__ }

            new_md_meta = {}
            new_md_meta['verbose_name'] = '%s (%s)' % (new_class.verbose_name, md_type)
            new_md_meta['verbose_name_plural'] = '%s (%s)' % (new_class.verbose_name_plural, md_type)
            new_md_meta['unique_together'] = base._meta.unique_together
            new_md_attrs['Meta'] = type("Meta", (), new_md_meta)
            return type("%s%s"%(name,"".join(md_type.split())), (base, MetaDataBaseModel), new_md_attrs.copy())

        # TODO: Move these names out of the way (subclasses will want to define their own attributes)
        if use_sites:
            new_class.PathMetaData = create_new_class('Path', SitePathMetaDataBase)
            new_class.ModelInstanceMetaData = create_new_class('Model Instance', SiteModelInstanceMetaDataBase)
            new_class.ModelMetaData = create_new_class('Model', SiteModelMetaDataBase)
            new_class.ViewMetaData = create_new_class('View', SiteViewMetaDataBase)
        else:
            new_class.PathMetaData = create_new_class('Path', PathMetaDataBase)
            new_class.ModelInstanceMetaData = create_new_class('Model Instance', ModelInstanceMetaDataBase)
            new_class.ModelMetaData = create_new_class('Model', ModelMetaDataBase)
            new_class.ViewMetaData = create_new_class('View', ViewMetaDataBase)

        registry[name] = new_class

        return new_class


    # TODO: Move this function out of the way (subclasses will want to define their own attributes)
    def _get_formatted_data(cls, path, context=None):
        """ Return an object to conveniently access the appropriate values. """
        return FormattedMetaData(cls(), cls._get_instances(path, context), path)


    # TODO: Move this function out of the way (subclasses will want to define their own attributes)
    def _get_instances(cls, path, context=None):
        """ A sequence of instances to discover metadata. 
            Each of the four meta data types are looked up when possible/necessary
        """
        try:
            yield cls.PathMetaData.objects.get_from_path(path)
        except cls.PathMetaData.DoesNotExist:
            pass

        try:
            i = cls.ModelInstanceMetaData.objects.get_from_path(path)
            yield i
            i2 = cls.ModelMetaData.objects.get_from_content_type(i._content_type)
            i2._set_context(i._content_object)
            yield i2
        except (cls.ModelInstanceMetaData.DoesNotExist, cls.ModelMetaData.DoesNotExist):
            pass

        try:
            i3 = cls.ViewMetaData.objects.get_from_path(path)
            i3._set_context(context)
            yield i3
        except cls.ViewMetaData.DoesNotExist:
            pass



class MetaData(object):
    __metaclass__ = MetaDataBase



def get_meta_data(path, name=None, context=None):
    # Find registered MetaData object
    if name is not None:
        try:
            metadata = registry[name]
        except KeyError:
            raise Exception("Meta data definition with name \"%s\" does not exist." % name)
    else:
        if len(registry) != 1:
            print registry.keys()
        assert len(registry) == 1, "You must have exactly one MetaData class, if using get_meta_data() without a 'name' parameter."
        metadata = registry.values()[0]
    return metadata._get_formatted_data(path, context)



def _update_callback(model_class, sender, instance, created, **kwargs):
    """ Callback to be attached to a post_save signal, updating the relevant
        meta data, or just creating an entry. 
    
        NB:
        It is theoretically possible that this code will lead to two instances
        with the same generic foreign key.  If you have non-overlapping URLs,
        then this shouldn't happen.
        I've held it to be more important to avoid double path entries.
    """
    meta_data = None
    content_type = ContentType.objects.get_for_model(instance)
    
    # If this object does not define a path, don't worry about automatic update
    try:
        path = instance.get_absolute_url()
    except AttributeError:
        return

    try:
        # Look for an existing object with this path
        meta_data = model_class.objects.get_from_path(path)
        # If another object has the same path, remove the path.
        # It's harsh, but we need a unique path and will assume the other
        # link is outdated.
        if meta_data._content_type != content_type or meta_data._object_id != instance.pk:
            meta_data._path = meta_data._content_object.get_absolute_url()
            meta_data.save()
            # Move on, this meta_data instance isn't for us
            meta_data = None
    except model_class.DoesNotExist:
        pass
    
    # If the path-based search didn't work, look for (or create) an existing
    # instance linked to this object.
    if not meta_data:
        meta_data, md_created = model_class.objects.get_or_create(_content_type=content_type, _object_id=instance.pk)
        meta_data._path = path
        meta_data.save()
    
    # XXX Update the MetaData instance with data from the object
    
def _delete_callback(model_class, sender, instance,  **kwargs):
    content_type = ContentType.objects.get_for_model(instance)
    try:
        model_class.objects.get(_content_type=content_type, _object_id=instance.pk).delete()
    except:
        pass


def register_signals():
    for meta_data_class in registry.values():
        update_callback = curry(_update_callback, model_class=meta_data_class.ModelInstanceMetaData)
        delete_callback = curry(_delete_callback, model_class=meta_data_class.ModelInstanceMetaData)

        ## Connect the models listed in settings to the update callback.
        for model in _get_seo_models(meta_data_class):
            models.signals.post_save.connect(update_callback, sender=model, weak=False)
            models.signals.pre_delete.connect(delete_callback, sender=model, weak=False)


