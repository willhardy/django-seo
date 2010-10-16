# -*- coding: utf-8 -*-

# TODO:
#    * ViewMetaData needs to resolve variables
#    * Validate bad field names (path, content_type etc) or even better: allow them by renaming system fields
#    * Admin!
#    * Tests!
#    * Documentation
#    * escape '"', maybe also '<', '>', '&' etc.
#    * ID and NAME tokens must begin with a letter ([A-Za-z]) and may be followed by any number of letters, digits ([0-9]), hyphens ("-"), underscores ("_"), colons (":"), and periods (".").

import re

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from rollyourown.seo.utils import strip_tags
from rollyourown.seo.modelmetadata import get_seo_content_types
from rollyourown.seo.systemviews import SystemViewField
from rollyourown.seo.utils import resolve_to_name

from django.template import Template, Context


registry = SortedDict()

VALID_HEAD_TAGS = "head title base link meta script".split()
VALID_INLINE_TAGS = (
    "area img object map param "
    "a abbr acronym dfn em strong "
    "code samp kbd var "
    "b i big small tt " # would like to leave these out :-)
    "span br bdo cite del ins q sub sup"
    # NB: deliberately leaving out iframe and script
).split()


class NotSet(object):
    " A singleton to identify unset values (where None would have meaning) "
    def __str__(self): return "NotSet"
    def __repr__(self): return self.__str__()
NotSet = NotSet()


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


class MetaDataField(object):
    creation_counter = 0

    def __init__(self, name, head, editable, populate_from, valid_tags, field, field_kwargs):
        self.name = name
        self.head = head
        self.editable = editable
        self.populate_from = populate_from
        # If valid_tags is a string, tags are space separated words
        if isinstance(valid_tags, basestring):
            valid_tags = valid_tags.split()
        self.valid_tags = set(valid_tags)
        self.field = field or models.CharField

        if field_kwargs is None: field_kwargs = {}
        self.field_kwargs = field_kwargs

        # Track creation order for field ordering
        self.creation_counter = MetaDataField.creation_counter
        MetaDataField.creation_counter += 1

    def contribute_to_class(self, cls, name):
        if not self.name:
            self.name = name
        self.validate()

    def validate(self):
        """ Discover certain illegal configurations """
        if not self.editable:
            assert self.populate_from is not NotSet, u"If field (%s) is not editable, you must set populate_from" % self.name

    def get_field(self):
        return self.field(**self.field_kwargs)

    def clean(self, value):
        return value

    def render(self, value):
        raise NotImplementedError


class Tag(MetaDataField):
    def __init__(self, name=None, head=False, escape_value=True,
                       editable=True, verbose_name=None, valid_tags=None, max_length=511,
                       populate_from=NotSet, field=models.CharField, 
                       field_kwargs=None, help_text=None):

        self.escape_value = escape_value
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('verbose_name', verbose_name)
        field_kwargs.setdefault('max_length', max_length)
        field_kwargs.setdefault('help_text', None)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)
        super(Tag, self).__init__(name, head, editable, populate_from, valid_tags, field, field_kwargs)

    def clean(self, value):
        if self.escape_value:
            value = conditional_escape(value)
        return mark_safe(value.strip())

    def render(self, value):
        return u'<%s>%s</%s>' % (self.name, value, self.name)


VALID_META_NAME = re.compile(r"[A-z][A-z0-9_:.-]*$")

class MetaTag(MetaDataField):
    def __init__(self, name=None, head=True, verbose_name=None, editable=True, 
                       populate_from=NotSet, valid_tags=None, max_length=511, field=models.CharField,
                       field_kwargs=None, help_text=None):
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('verbose_name', verbose_name)
        field_kwargs.setdefault('max_length', max_length)
        field_kwargs.setdefault('help_text', None)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)

        if name is not None:
            assert VALID_META_NAME.match(name) is not None, u"Invalid name for MetaTag: '%s'" % name

        super(MetaTag, self).__init__(name, head, editable, populate_from, valid_tags, field, field_kwargs)

    def clean(self, value):
        return value.replace('"', '&#34;').replace("\n", " ").strip()

    def render(self, value):
        # TODO: HTML/XHTML?
        return mark_safe(u'<meta name="%s" content="%s" />' % (self.name, value))

class KeywordTag(MetaTag):
    def __init__(self, name=None, head=True, verbose_name=None, editable=True, 
                       populate_from=NotSet, valid_tags=None, max_length=511, field=models.CharField,
                       field_kwargs=None, help_text=None):
        if name is None:
            name = "keywords"
        if valid_tags is None:
            valid_tags = []
        super(KeywordTag, self).__init__(name, head, verbose_name, editable, 
                        populate_from, valid_tags, max_length, field, 
                        field_kwargs, help_text)

    def clean(self, value)
        return value.replace('"', '&#34;').replace("\n", ", ").strip()


class Raw(MetaDataField):
    def __init__(self, head=True, editable=True, populate_from=NotSet, 
                    verbose_name=None, valid_tags=None, field=models.TextField,
                    field_kwargs=None, help_text=None):
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('help_text', None)
        field_kwargs.setdefault('verbose_name', verbose_name)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)
        super(Raw, self).__init__(None, head, editable, populate_from, valid_tags, field, field_kwargs)

    def clean(self, value):
        # TODO: escape/strip all but self.valid_tags
        if self.head:
            value = strip_tags(value, VALID_HEAD_TAGS)
        return mark_safe(value)

    def render(self, value):
        return value



class PathMetaDataManager(models.Manager):
    def get_from_path(self, path):
        return self.get_query_set().get(path=path)

class ModelMetaDataManager(models.Manager):
    def get_from_content_type(self, content_type):
        return self.get_query_set().get(content_type=content_type)

class ModelInstanceMetaDataManager(models.Manager):
    def get_from_path(self, path):
        return self.get_query_set().get(path=path)

class ViewMetaDataManager(models.Manager):
    def get_from_path(self, path):
        view_name = resolve_to_name(path)
        if view_name is not None:
            return self.get_query_set().get(view=view_name)
        raise self.model.DoesNotExist()

class MetaDataBase(type):
    def __new__(cls, name, bases, attrs):
        # TODO: Think of a better test to avoid processing MetaData parent class
        if bases == (object,):
            return super(MetaDataBase, cls).__new__(cls, name, bases, attrs)

        # Save options as a dict for now (we will be editing them)
        # TODO: Is this necessary, should we bother passing through Django Meta options?
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

        # TODO: Reorganise? should this go somewhere else?
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

        # 1. Path-based model
        class PathMetaData(MetaDataBaseModel):
            path = models.CharField(_('path'), max_length=511, unique=True)
            objects = PathMetaDataManager()
            _meta_data = new_class

            class Meta:
                verbose_name = _('path-based metadata')
                verbose_name_plural = _('path-based metadata')
                #app_label = None # TODO

        # 2. Model-based model
        class ModelMetaData(MetaDataBaseModel):
            content_type   = models.ForeignKey(ContentType, null=True, blank=True, unique=True,
                                        limit_choices_to={'id__in': get_seo_content_types()})
            objects = ModelMetaDataManager()
            _meta_data = new_class

            def _set_context(self, instance):
                """ Use the given model instance as context for rendering 
                    any substitutions. 
                """
                self.__instance = instance

            def __getattribute__(self, name):
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
            path           = models.CharField(_('path'), max_length=511, unique=True)
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
            view = SystemViewField(blank=True, null=True, unique=True)
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


