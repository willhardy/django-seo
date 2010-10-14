# -*- coding: utf-8 -*-

# TODO:
#    * ViewMetaData and ModelMetaData need to resolve variables
#    * Signal handlers for ModelInstanceMetaData
#    * Tests!
#    * Documentation

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.exceptions import ObjectDoesNotExist

from seo import settings
from seo.utils import strip_for_head
from seo.modelmetadata import get_seo_content_types
from seo.viewmetadata import SystemViewField
from seo.utils import resolve_to_name

# Not yet used (but probably will be soon)
from seo.utils import get_seo_models
from django.template import Template, Context


class NotSet(object):
    " A singleton to identify unset values (where None would have meaning) "
NotSet = NotSet()


class Literal(object):
    " Wrap literal values so that the system knows to treat them that way "
    def __init__(self, value):
        self.value = value


class FormattedMetaData(object):
    """ Allows convenient access to selected metadata.
        Metadata for each field may be sourced from any one of the relevant instances passed.
    """

    def __init__(self, metadata, *instances):
        # For defaults
        self.metadata = metadata
        # instances usually path_metadata, view_metadata, model_metadata
        self.instances = instances


    def _resolve_value(self, name):
        """ Returns an appropriate value for the given name. """
        if name in self.metadata.elements:
            # Look in instances for an explicit value
            for instance in self.instances:
                value = getattr(instance, name)
                if value:
                    return value

            # Otherwise, return an appropriate default value (populate_from)
            populate_from = self.metadata.elements[name].populate_from
            if callable(populate_from):
                return populate_from()
            elif isinstance(populate_from, Literal):
                return populate_from.value
            else:
                return self._resolve_value(self, populate_from)

        # If this is not an element, look for an attribute on metadata
        # TODO: use try/except AttributeError?
        elif hasattr(self.metadata, name):
            value = getattr(self.metadata, name)
            if callable(value):
                return value()
            else:
                return value

        # Look for an attribute on the instances
        # TODO: use try/except AttributeError?
        for instance in self.instances:
            if hasattr(instance, name):
                value = getattr(instance, name)
                if callable(value):
                    return value()
                else:
                    return value


    def __getattr__(self, name):
        # Look for a group called "name"
        if name in self.metadata.groups:
            return '\n'.join(self._resolve_value(f) for f in self.metadata.groups[name])
        # Look for an element called "name"
        elif name in self.metadata.elements:
            return self._resolve_value(name)
        else:
            raise AttributeError

    def __unicode__(self):
        """ String version of this object is the html output of head elements. """
        # TODO: If groups are given, pull those values out and keep them together
        return '\n'.join(self._resolve_value(f) for f,e in self.metadata.elements.items() if e.head)


class MetaDataField(object):
    creation_counter = 0

    def __init__(self, name, head, editable, populate_from, field, field_kwargs):
        self.name = name
        self.head = head
        self.editable = editable
        self.populate_from = populate_from
        self.field = field or models.CharField

        if field_kwargs is None: field_kwargs = {}
        self.field_kwargs = field_kwargs

        # Track creation order for field ordering
        self.creation_counter = MetaDataField.creation_counter
        MetaDataField.creation_counter += 1

    def contribute_to_class(self, cls, name):
        if not self.name:
            self.name = name

    def get_field(self):
        return self.field(**self.field_kwargs)

    def render(self, value):
        raise NotImplementedError


class Tag(MetaDataField):
    def __init__(self, name=None, head=False, escape_value=True,
                       editable=True, populate_from=NotSet,
                       field=models.CharField, field_kwargs=None):
        self.name = name
        self.escape_value = escape_value
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('max_length', 511)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)
        super(Tag, self).__init__(head, editable, populate_from, field, field_kwargs)

    def render(self, value):
        if self.escape_value:
            value = conditional_escape(value)
        name = conditional_escape(name).replace(' ', '')
        return mark_safe(u'<%s>%s</%s>' % (name, value, name))


class MetaTag(MetaDataField):
    def __init__(self, name=None, head=True,
                       editable=True, populate_from=NotSet,
                       field=models.CharField, field_kwargs=None):
        self.name = name
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('max_length', 511)
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)
        super(Tag, self).__init__(head, editable, populate_from, field, field_kwargs)

    def render(self, value):
        # TODO: HTML/XHTML? Use template?
        value = value.replace('"', '&#34;')
        name = self.name.replace('"', '&#34;')
        return mark_safe(u'<meta name="%s" content="%s" />' % (name, value))


class Raw(MetaDataField):
    def __init__(self, head=True, editable=True, populate_from=NotSet,
                                field=models.TextField, field_kwargs=None):
        if field_kwargs is None: 
            field_kwargs = {}
        field_kwargs.setdefault('default', "")
        field_kwargs.setdefault('blank', True)
        super(Tag, self).__init__(None, head, editable, populate_from, field, field_kwargs)

    def render(self, value):
        if self.head:
            value = strip_for_head(value)
        return mark_safe(value)



class PathMetaDataManager(models.Manager):
    def get_from_path(self, path):
        return self.get_query_set().get(path=path)

## TODO: ModelMetaData only works if you have a modelinstance
class ModelMetaDataManager(models.Manager):
    def get_from_path(self, path):
        #return self.model.ModelInstanceMetaData.objects.get(path=path)
        return

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

        # Save options as a dict for now (we will be editing them)
        # TODO: Is this necessary, should we bother passing through Django Meta options?
        Meta = attrs.pop('Meta', {})
        if Meta:
            Meta = Meta.__dict__.copy()

        # Remove our options from Meta, so Django won't complain
        groups = Meta.pop('groups', {})
        use_sites = Meta.pop('use_sites', False)
        help_text = attrs.pop('HelpText', {})

        # Collect and sort our elements
        elements = [(key, attrs.pop(key)) for key, obj in attrs.items() 
                                        if isinstance(obj, MetaDataField)]
        elements.sort(lambda x, y: cmp(x[1].creation_counter, 
                                                y[1].creation_counter))
        elements = SortedDict(elements)

        # Validation:
        # Check that no group names clash with element names
        for key in groups:
            if key in elements:
                raise Exception("Group name '%s' clashes with field name" % key)

        # Preprocessing complete, here is the new class
        new_class = super(MetaDataBase, cls).__new__(cls, name, bases, attrs)

        # Some useful attributes
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
            fields['site'] = models.ForeignKey('contenttypes.Site', default=settings.SITE_ID)
        MetaDataBaseModel = type('%sBase' % name, (models.Model,), fields)

        # 1. Path-based model
        class PathMetaData(MetaDataBaseModel):
            path = models.CharField(_('path'), max_length=511, unique=True)
            objects = PathMetaDataManager()

            class Meta:
                verbose_name = _('path-based metadata')
                verbose_name_plural = _('path-based metadata')
                #app_label = None # TODO

        # 2. Model-based model
        class ModelMetaData(MetaDataBaseModel):
            content_type   = models.ForeignKey(ContentType, null=True, blank=True, unique=True,
                                        limit_choices_to={'id__in': get_seo_content_types()})
            objects = ModelMetaDataManager()

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
            content_object = generic.GenericForeignKey('content_type', 'object_id'),
            objects = ModelInstanceMetaDataManager()

            class Meta:
                verbose_name = _('model-instance-based metadata')
                verbose_name_plural = _('model-instance-based metadata')
                unique_together = ('content_type', 'object_id')
                # app_label = None # TODO

        # 4. View-based model
        class ViewMetaData(MetaDataBaseModel):
            view = SystemViewField(blank=True, null=True, unique=True)
            objects = ViewMetaDataManager()

            class Meta:
                verbose_name = _('view-based metadata')
                verbose_name_plural = _('view-based metadata')
                # app_label = None # TODO

        new_class.PathMetaData = PathMetaData
        new_class.ModelMetaData = ModelMetaData
        new_class.ModelInstanceMetaData = ModelInstanceMetaData
        new_class.ViewMetaData = ViewMetaData

        return new_class


class MetaData(object):
    __metaclass__ = MetaDataBase

    def get_formatted_data(self, path):
        """ Return an object to conveniently access the appropriate values. """
        instances = [
            ProxyInstance(self.PathMetaData, path),
            ProxyInstance(self.ModelMetaData, path),
            ProxyInstance(self.ModelInstanceMetaData, path),
            ProxyInstance(self.PathMetaData, path),
            ]

        return FormattedMetaData(self, *instances)


def get_meta_data(path, name=None):
    # Find registered MetaData object
    if name is not None:
        metadata = registry[name]
    else:
        assert len(registry) == 1, "You must have exactly one MetaData class, if using get_meta_data() without a 'name' parameter."
        metadata = registry.values()[0]
    return metadata.get_formatted_data(path)


class ProxyInstance(object):
    """ This is a simple proxy to prevent unnecessary queries.
        It should only be used in the context of resolving an attribute lookup
        over several instances.
        TODO: This could use __attributes
    """
    def __init__(self, model, path):
        self._model = model
        self._path = path

    @property
    def _instance(self):
        # If there is no model, there is no hope
        if self._model is None:
            return None
        if not hasattr(self, '_instance_cache'):
            try:
                self._instance_cache = self._model.objects.get_from_path(path=self._path)
            except ObjectDoesNotExist:
                # There is no hope
                self._model = None
                return None
        return self._instance_cache

    def __get__(self, name):
        return getattr(self._instance, name)







# OLD CLASSES/FUNCTIONS
# Kept for reference, remove when new API is complete


def template_meta_data(path=None):
    """ Returns a formatted meta data object for the given path. """
    # TODO: Move away, take request as an argument?
    view_meta_data = None

    if path is None:
        meta_data = MetaData()
    else:
        try:
            meta_data = MetaData.objects.get(path=path)
        except MetaData.DoesNotExist:
            meta_data = MetaData()

        view_name = resolve_to_name(path)
        if view_name is not None:
            try:
                view_meta_data = ViewMetaData.objects.get(view=view_name)
            except (MetaData.DoesNotExist, ):
                pass
            
    return FormattedMetaData(meta_data, view_meta_data=view_meta_data)


# For ModelMetaData: resolve the string substitution using the relevant model
    def _get_category_value(self, name):
        """ Retrieve a value from a category meta data object, 
            allowing a single point of control for an entire content type.
        """
        val = getattr(self._meta_data.category_meta_data, name, None)
        if val and self._meta_data.object_id:
            # Substitute variables
            val = val.replace(u"%s", u"%%s")
            # Handle keyword substituion "one two %(name)s three"
            val = _resolve(val,self._meta_data.content_object)
        return val

def _resolve(value, model_instance=None, context_instance=None):
    """ Resolves any template references in the given value. 
    """
    if context_instance is None:
        context_instance = Context()
    if model_instance is not None:
        context_instance[model_instance._meta.module_name] = model_instance
    if "{" in value and context_instance is not None:
        value = Template(value).render(context_instance)
    return value


# ModelInstanceMetaData needs to be linked to the relevant instance

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
    if not hasattr(instance, 'get_absolute_url'):
        return
    path = instance.get_absolute_url()

    if path:
        try:
            # Look for an existing object with this path
            meta_data = MetaData.objects.get(path=path)
            # If a path is defined, but the content_type and object_id aren't, 
            # then adopt this object
            if not meta_data.content_type:
                meta_data.content_type = content_type
                meta_data.object_id = instance.pk
            # If another object has the same path, remove the path.
            # It's harsh, but we need a unique path and will assume the other
            # link is outdated.
            elif meta_data.content_type != content_type or meta_data.object_id != instance.pk:
                meta_data.path = None
                meta_data.save()
                # Move on, this meta_data instance isn't for us
                meta_data = None
        except MetaData.DoesNotExist:
            pass

        # If the path-based search didn't work, look for (or create) an existing
        # instance linked to this object.
        if not meta_data:
            meta_data, md_created = MetaData.objects.get_or_create(content_type=content_type, object_id=instance.pk)
            meta_data.path=path
            meta_data.save()

        # Update the MetaData instance with data from the object
        if meta_data.update_from_related_object():
            meta_data.save(update_related=False)

def delete_callback(sender, instance,  **kwargs):
    content_type = ContentType.objects.get_for_model(instance)
    try:
        MetaData.objects.get(content_type=content_type, object_id=instance.pk).delete()
    except:
        pass

## Connect the models listed in settings to the update callback.
for model in get_seo_models():
    models.signals.post_save.connect(update_callback, sender=model)
    models.signals.pre_delete.connect(delete_callback, sender=model)


