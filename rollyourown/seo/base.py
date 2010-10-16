# -*- coding: utf-8 -*-

# TODO:
#    * ViewMetaData needs to resolve variables
#    * Validate bad field names (path, content_type etc) or even better: allow them by renaming system fields
#    * Add unique constraints for models with/without sites support
#    * Admin!
#    * Tests!
#    * Documentation
#    * Review escaping: check that autoescape is working. remove '"' in meta tags (maybe also '<', '>', '&')

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.conf import settings

from rollyourown.seo.modelmetadata import get_seo_content_types
from rollyourown.seo.systemviews import SystemViewField
from rollyourown.seo.utils import resolve_to_name, NotSet

from django.template import Template, Context
from rollyouown.seo.fields import MetaDataField
from rollyouown.seo.fields import TagField, MetaTagField, KeywordTag, RawField


registry = SortedDict()


class Literal(object):
    " Wrap literal values so that the system knows to treat them that way "
    def __init__(self, value):
        self.value = value


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
        """ Returns an appropriate value for the given name. """
        name = str(name)
        if name in self.__metadata.elements:
            # Look in instances for an explicit value
            for instance in self.__instances():
                value = getattr(instance, name)
                if value:
                    return BoundMetaDataField(self.__metadata.elements[name], value)

            # Otherwise, return an appropriate default value (populate_from)
            populate_from = self.__metadata.elements[name].populate_from
            if callable(populate_from):
                return populate_from()
            elif isinstance(populate_from, Literal):
                return populate_from.value
            elif populate_from is not NotSet:
                return self._resolve_value(populate_from)

        # If this is not an element, look for an attribute on metadata
        try:
            value = getattr(self.__metadata, name)
        except AttributeError:
            pass
        else:
            if callable(value):
                return value()
            return value

    def __getattr__(self, name):
        # Look for a group called "name"
        if name in self.__metadata.groups:
            return '\n'.join(self._resolve_value(f) for f in self.__metadata.groups[name])
        # Look for an element called "name"
        elif name in self.__metadata.elements:
            return self._resolve_value(name)
        else:
            raise AttributeError

    def __unicode__(self):
        """ String version of this object is the html output of head elements. """
        return '\n'.join(map(unicode, filter(None, (self._resolve_value(f) for f,e in self.__metadata.elements.items() if e.head))))


class BoundMetaDataField(object):
    """ An object to help provide templates with access to a "bound" meta data field. """

    def __init__(self, field, value):
        self.field = field
        self.value = field.clean(value)

    def __unicode__(self):
        return self.field.render(self.value)

    def __str__(self):
        return self.__unicode__().encode("ascii", "ignore")


class MetaDataManager(models.Manager):
    def on_current_site():
        queryset = super(MetaDataManager, self).get_query_set()
        # If we are using sites, exclude irrelevant data
        if self.model._meta_data.use_sites:
            current_site = Site.objects.get_current()
            # Exclude entries for other sites, keep site=current and site=null
            queryset = queryset.exclude(~models.Q(site=current_site))
        return queryset

class PathMetaDataManager(MetaDataManager):
    def get_from_path(self, path):
        return self.on_current_site().get(path=path)

class ModelMetaDataManager(MetaDataManager):
    def get_from_content_type(self, content_type):
        return self.on_current_site().get(content_type=content_type)

class ModelInstanceMetaDataManager(MetaDataManager):
    def get_from_path(self, path):
        return self.on_current_site().get(path=path)

class ViewMetaDataManager(MetaDataManager):
    def get_from_path(self, path):
        view_name = resolve_to_name(path)
        if view_name is not None:
            return self.on_current_site().get(view=view_name)
        raise self.model.DoesNotExist()

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
        for key in groups:
            assert key not in elements, "Group name '%s' clashes with field name" % key

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
            verbose_name = _('metadata')
            verbose_name_plural = _('metadata')
            app_label = None # TODO
        fields['Meta'] = BaseMeta
        if use_sites: # and Site.objects.is_installed():
            fields['site'] = models.ForeignKey('contenttypes.Site', default=settings.SITE_ID, null=True, blank=True)
        fields['__module__'] = attrs['__module__']
        MetaDataBaseModel = type('%sBase' % name, (models.Model,), fields)

        # TODO Move the definitions for each particular class to another module and mixin.
        # 1. Path-based model
        class PathMetaData(MetaDataBaseModel):
            path = models.CharField(_('path'), max_length=511)
            objects = PathMetaDataManager()
            _meta_data = new_class

            class Meta:
                verbose_name = _('path-based metadata')
                verbose_name_plural = _('path-based metadata')
                #app_label = None # TODO

        # 2. Model-based model
        class ModelMetaData(MetaDataBaseModel):
            content_type   = models.ForeignKey(ContentType, null=True, blank=True,
                                        limit_choices_to={'id__in': get_seo_content_types()})
            objects = ModelMetaDataManager()
            _meta_data = new_class

            def _set_context(self, instance):
                """ Use the given model instance as context for rendering 
                    any substitutions. 
                """
                self.__instance = instance

            def __getattribute__(self, name):
                # Any values coming from elements should be parsed and resolved.
                value = super(ModelMetaData, self).__getattribute__(name)
                if (name in (f.name for f in super(ModelMetaData, self).__getattribute__('_meta').fields) 
                    and '_ModelMetaData__instance' in super(ModelMetaData, self).__getattribute__('__dict__')):
                    instance = super(ModelMetaData, self).__getattribute__('_ModelMetaData__instance')
                    return _resolve(value, instance)
                else: 
                    return value

            class Meta:
                verbose_name = _('model-based metadata')
                verbose_name_plural = _('model-based metadata')
                # app_label = None # TODO

        # 3. Model-instance-based model
        class ModelInstanceMetaData(MetaDataBaseModel):
            path           = models.CharField(_('path'), max_length=511)
            content_type   = models.ForeignKey(ContentType, null=True, blank=True,
                                        limit_choices_to={'id__in': get_seo_content_types()})
            object_id      = models.PositiveIntegerField(null=True, blank=True, editable=False)
            content_object = generic.GenericForeignKey('content_type', 'object_id')
            objects = ModelInstanceMetaDataManager()
            _meta_data = new_class

            class Meta:
                verbose_name = _('model-instance-based metadata')
                verbose_name_plural = _('model-instance-based metadata')
                unique_together = ('content_type', 'object_id')
                # app_label = None # TODO

        # 4. View-based model
        class ViewMetaData(MetaDataBaseModel):
            view = SystemViewField(blank=True, null=True)
            objects = ViewMetaDataManager()
            _meta_data = new_class

            class Meta:
                verbose_name = _('view-based metadata')
                verbose_name_plural = _('view-based metadata')
                # app_label = None # TODO

        # TODO: Move these out of the way (subclasses will want to define their own attributes)
        new_class.PathMetaData = PathMetaData
        new_class.ModelMetaData = ModelMetaData
        new_class.ModelInstanceMetaData = ModelInstanceMetaData
        new_class.ViewMetaData = ViewMetaData

        registry[name] = new_class

        return new_class


    # TODO: Move this function out of the way (subclasses will want to define their own attributes)
    def _get_formatted_data(cls, path):
        """ Return an object to conveniently access the appropriate values. """
        return FormattedMetaData(cls, cls._get_instances(path))


    # TODO: Move this function out of the way (subclasses will want to define their own attributes)
    def _get_instances(cls, path):
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
            yield cls.ViewMetaData.objects.get_from_path(path)
        except cls.ViewMetaData.DoesNotExist:
            pass


    # TODO: Move this function out of the way (subclasses will want to define their own attributes)
    def _get_seo_models(cls):
        """ Gets the actual models to be used. """
        seo_models = []
        for model_name in cls.seo_models:
            if "." in model_name:
                app_label, model_name = model_name.split(".", 1)
                model = models.get_model(app_label, model_name)
                if model:
                    seo_models.append(model)
            else:
                app = models.get_app(model_name)
                if app:
                    seo_models.extend(models.get_models(app))

        return seo_models


class MetaData(object):
    __metaclass__ = MetaDataBase


def get_meta_data(path, name=None):
    # Find registered MetaData object
    if name is not None:
        metadata = registry[name]
    else:
        assert len(registry) == 1, "You must have exactly one MetaData class, if using get_meta_data() without a 'name' parameter."
        metadata = registry.values()[0]
    return metadata._get_formatted_data(path)


def _resolve(value, model_instance=None, context_instance=None):
    """ Resolves any template references in the given value. 
    """
    if isinstance(value, basestring) and "{" in value:
        if context_instance is None:
            context_instance = Context()
        if model_instance is not None:
            context_instance[model_instance._meta.module_name] = model_instance
        value = Template(value).render(context_instance)
    return value


def register_signals():
    for meta_data_class in registry.values():
        ModelInstanceMetaData = meta_data_class.ModelInstanceMetaData

        def update_callback(sender, instance, created, **kwargs):
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
                meta_data = ModelInstanceMetaData.objects.get_from_path(path)
                # If another object has the same path, remove the path.
                # It's harsh, but we need a unique path and will assume the other
                # link is outdated.
                if meta_data.content_type != content_type or meta_data.object_id != instance.pk:
                    meta_data.path = meta_data.content_object.get_absolute_url()
                    meta_data.save()
                    # Move on, this meta_data instance isn't for us
                    meta_data = None
            except ModelInstanceMetaData.DoesNotExist:
                pass
    
            # If the path-based search didn't work, look for (or create) an existing
            # instance linked to this object.
            if not meta_data:
                meta_data, md_created = ModelInstanceMetaData.objects.get_or_create(content_type=content_type, object_id=instance.pk)
                meta_data.path = path
                meta_data.save()
    
            # XXX Update the MetaData instance with data from the object
    
        def delete_callback(sender, instance,  **kwargs):
            content_type = ContentType.objects.get_for_model(instance)
            try:
                ModelInstanceMetaData.objects.get(content_type=content_type, object_id=instance.pk).delete()
            except:
                pass
    
        ## Connect the models listed in settings to the update callback.
        for model in meta_data_class._get_seo_models():
            models.signals.post_save.connect(update_callback, sender=model, weak=False)
            models.signals.pre_delete.connect(delete_callback, sender=model, weak=False)


