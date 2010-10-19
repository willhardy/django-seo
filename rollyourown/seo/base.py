# -*- coding: utf-8 -*-

# TODO:
#    * Validate bad field names (path, content_type etc) or even better: allow them by renaming system fields
#    * Help Text not showing in Admin
#    * Add unique constraints for models with/without sites support
#    * Caching
#    * Documentation

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from django.utils.functional import curry
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils.safestring import mark_safe

from rollyourown.seo.utils import NotSet, Literal

from rollyourown.seo.fields import MetaDataField
from rollyourown.seo.fields import Tag, MetaTag, KeywordTag, Raw
from rollyourown.seo.meta_models import PathMetaDataBase, ModelMetaDataBase, ModelInstanceMetaDataBase, ViewMetaDataBase, _get_seo_models
from rollyourown.seo.meta_models import PathMetaDataManager, ModelMetaDataManager, ModelInstanceMetaDataManager, ViewMetaDataManager


registry = SortedDict()


class FormattedMetaData(object):
    """ Allows convenient access to selected metadata.
        Metadata for each field may be sourced from any one of the relevant instances passed.
    """

    def __init__(self, metadata, instances):
        self.__metadata = metadata
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
                if getattr(populate_from, 'im_self', None):
                    return populate_from()
                else:
                    return populate_from(self.__metadata)
            elif isinstance(populate_from, Literal):
                return populate_from.value
            elif populate_from is not NotSet:
                return self._resolve_value(populate_from)

    def __getattr__(self, name):
        # Look for a group called "name"
        if name in self.__metadata.groups:
            return '\n'.join(BoundMetaDataField(self.__metadata.elements[name], self._resolve_value(f)) for f in self.__metadata.groups[name])
        # Look for an element called "name"
        elif name in self.__metadata.elements:
            return BoundMetaDataField(self.__metadata.elements[name], self._resolve_value(name))
        else:
            raise AttributeError

    def __unicode__(self):
        """ String version of this object is the html output of head elements. """
        return mark_safe(u'\n'.join(unicode(getattr(self, f)) for f,e in self.__metadata.elements.items() if e.head))


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
        if help_text:
            help_text = help_text.__dict__.copy()

        # Collect and sort our elements
        elements = [(key, attrs.pop(key)) for key, obj in attrs.items() 
                                        if isinstance(obj, MetaDataField)]
        elements.sort(lambda x, y: cmp(x[1].creation_counter, 
                                                y[1].creation_counter))
        elements = SortedDict(elements)

        # Validation:
        # Check that no group names clash with element names
        # TODO: Write a test framework for seo.MetaData validation
        for key,members in groups.items():
            assert key not in elements, "Group name '%s' clashes with field name" % key
            for member in members:
                assert member in elements, "Group member '%s' is not a valid field" % member

        # Preprocessing complete, here is the new class
        new_class = super(MetaDataBase, cls).__new__(cls, name, bases, attrs)

        # Some useful attributes
        # TODO: Move these out of the way (subclasses will want to use their own attributes)
        new_class.seo_models = seo_models
        new_class.elements = elements
        new_class.groups = groups
        new_class.use_sites = use_sites

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
                populate_from = getattr(field, 'populate_from', None)
                # Add field help text if missing, add something useful
                if not field.help_text:
                    if key in help_text:
                        field.help_text = help_text[key]
                    elif populate_from and populate_from in elements:
                        field.help_text = _("If empty, %s will be used") % elements[populate_from].verbose_name
                    elif populate_from and hasattr(populate_from, 'short_description'):
                        field.help_text = _("If empty: %s.") % populate_from.short_description
                fields[key] = field

        # 0. Abstract base model with common fields
        base_meta = type('Meta', (), Meta)
        class BaseMeta(base_meta):
            abstract = True
            app_label = 'seo'
        fields['Meta'] = BaseMeta
        fields['__module__'] = attrs['__module__']
        MetaDataBaseModel = type('%sBase' % name, (models.Model,), fields)

        # TODO: Move these names out of the way (subclasses will want to define their own attributes)
        new_md_attrs = {'_meta_data': new_class, '__module__': __name__ }
        if use_sites: # and Site.objects.is_installed():
            new_md_attrs['site'] = models.ForeignKey(Site, default=settings.SITE_ID, null=True, blank=True)
        new_class.PathMetaData = type("%sPathMetaData"%name, (PathMetaDataBase, MetaDataBaseModel), new_md_attrs.copy())
        new_class.ModelMetaData = type("%sModelMetaData"%name, (ModelMetaDataBase, MetaDataBaseModel), new_md_attrs.copy())
        new_class.ModelInstanceMetaData = type("%sModelInstanceMetaData"%name, (ModelInstanceMetaDataBase, MetaDataBaseModel), new_md_attrs.copy())
        new_class.ViewMetaData = type("%sViewMetaData"%name, (ViewMetaDataBase, MetaDataBaseModel), new_md_attrs.copy())

        registry[name] = new_class

        return new_class


    # TODO: Move this function out of the way (subclasses will want to define their own attributes)
    def _get_formatted_data(cls, path, context=None):
        """ Return an object to conveniently access the appropriate values. """
        return FormattedMetaData(cls(), cls._get_instances(path, context))


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
            i2 = cls.ModelMetaData.objects.get_from_content_type(i.content_type)
            i2._set_context(i.content_object)
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
        metadata = registry[name]
    else:
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
        if meta_data.content_type != content_type or meta_data.object_id != instance.pk:
            meta_data.path = meta_data.content_object.get_absolute_url()
            meta_data.save()
            # Move on, this meta_data instance isn't for us
            meta_data = None
    except model_class.DoesNotExist:
        pass
    
    # If the path-based search didn't work, look for (or create) an existing
    # instance linked to this object.
    if not meta_data:
        meta_data, md_created = model_class.objects.get_or_create(content_type=content_type, object_id=instance.pk)
        meta_data.path = path
        meta_data.save()
    
    # XXX Update the MetaData instance with data from the object
    
def _delete_callback(model_class, sender, instance,  **kwargs):
    content_type = ContentType.objects.get_for_model(instance)
    try:
        model_class.objects.get(content_type=content_type, object_id=instance.pk).delete()
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


