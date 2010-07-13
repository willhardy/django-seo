# -*- coding: utf-8 -*-

""" 
    Model definition for django seo app.
    To use this app:
        1. Install the seo directory somewhere in your python path
        2. Add 'seo' to INSTALLED_APPS
        3. If you would like to reference objects, define SEO_MODELS in settings
           as a list of model or app names eg ('flatpages.FlatPage', 'blog',)
        4. Do one or both of the following
          a) Add 'seo.context_processors.seo' to TEMPLATE_CONTEXT_PROCESSORS
             and reference {{ seo_meta_data }} in your (eg base) template
          b) Add 'seo.middleware.MetaDataMiddleware' to MIDDLEWARE and
             make sure meta data isn't already defined in the template.

"""

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.urlresolvers import Resolver404
from seo.utils import get_seo_models, resolve_to_name
from seo.modelmetadata import get_seo_content_types
from seo.viewmetadata import SystemViewField
from django.template.defaultfilters import striptags
from django.utils.safestring import mark_safe
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.template import Template, Context
from django.utils.functional import lazy
try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# TODO: Document the use of these
DEFAULT_TITLE       = getattr(settings, "SEO_DEFAULT_TITLE", "")
DEFAULT_KEYWORDS    = getattr(settings, "SEO_DEFAULT_KEYWORDS", "")
DEFAULT_DESCRIPTION = getattr(settings, "SEO_DEFAULT_DESCRIPTION", "")
CONTEXT_VARIABLE    = getattr(settings, "SEO_CONTEXT_VARIABLE", 'seo_meta_data')

if not DEFAULT_TITLE and Site._meta.installed:
    # Because we are in models.py, the Site information 
    # wont be available until the tables have been created
    def get_current_site_title():
        current_site = Site.objects.get_current()
        return current_site.name or current_site.domain
    DEFAULT_TITLE = lazy(get_current_site_title, unicode)()

TEMPLATE = "seo/head.html"

def template_meta_data(path=None):
    if path is None:
        meta_data = MetaData()
        view_meta_data = None
    else:
        try:
            meta_data = MetaData.objects.get(path=path)
        except MetaData.DoesNotExist:
            meta_data = MetaData()
        try:
            view_meta_data = ViewMetaData.objects.get(view=resolve_to_name(path))
        except (MetaData.DoesNotExist, Resolver404):
            view_meta_data = None
            
    return TemplateMetaData(meta_data, view_meta_data=view_meta_data)


class MetaData(models.Model):
    """ Contains meta information for a page in a django-based site.
        This can be associated with a page in one of X ways:
            1) setting the generic foreign key to an object with get_absolute_url (path is set automatically)
            2) setting the URL manually

        PROBLEMS:
        * One problem that can occur if the URL is manually overridden and it no
          longer matches the linked object. Not sure what to do here.
        * Overridden title information is not relayed back to the object (not too important)
        
    """

    # These fields can be manually overridden or populated from the object itself.
    # If there is a conflict the information in the object currently being saved is preserved
    path        = models.CharField(max_length=255, blank=True, null=True, unique=True, help_text="Specify the path (URL) for this page (only if no object is linked).")
    title       = models.CharField(max_length=511, default="", blank=True, help_text="This is the meta (page) title, that appears in the title bar.")
    heading     = models.CharField(max_length=511, default="", blank=True, help_text="This is the page heading, that appears in the &lt;h1&gt; tag.")
    subheading  = models.CharField(max_length=511, default="", blank=True, help_text="This is the page subheading, that appears near the &lt;h1&gt; tag.")
    keywords    = models.TextField(default="", blank=True, help_text="Comma-separated keywords for search engines.")
    description = models.TextField(default="", blank=True, help_text="A short description, displayed in search results.")
    extra       = models.TextField(default="", blank=True, help_text="(advanced) Any additional HTML to be placed verbatim in the &lt;head&gt;")

    # If the generic foreign key is set, populate the above fields from there
    content_type   = models.ForeignKey(ContentType, null=True, blank=True,
                                        limit_choices_to={'id__in': get_seo_content_types()})
    object_id      = models.PositiveIntegerField(null=True, blank=True, editable=False)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ("path",)
        verbose_name = u"metadata"
        verbose_name_plural = u"metadata"

    def get_absolute_url(self):
        if self.path:
            return self.path

    def __unicode__(self):
        return self.title or self.heading or self.description or "(blank: %s)" % self.path

    def save(self, update_related=True, *args, **kwargs):
        self.keywords = ", ".join(self.keywords.strip().splitlines())
        self.description = " ".join(self.description.strip().splitlines())
        self.extra = strip_for_head(self.extra.strip())
        super(MetaData, self).save(*args, **kwargs)
        if update_related:
            self.update_related_object()

    def update_related_object(self):
        """ Helps ensure that denormalised data is synchronised. 
            That is, if data is discovered through explicit fields, these are 
        """
        instance = self.content_object
        if instance:
            attrs = {}

            # Only populate the fields that are explicity defined
            fields = instance._meta.get_all_field_names()
            if 'meta_description' in fields:
                attrs['meta_description'] = self.description
            if 'meta_keywords' in fields:
                attrs['meta_keywords'] = self.keywords
            if 'meta_title' in fields:
                attrs['meta_title'] = self.title

            if attrs:
                # Update the data in the related object. 
                # Note that we shouldn't trigger the post_save signal
                self.content_type.model_class()._default_manager.filter(pk=self.object_id).update(**attrs)

    def update_from_related_object(self):
        """ Updats the meta data from the related object, returning true if 
            changes have been made. 
        """
        if self.content_object:
            # Populate core fields if the object explicitly defines them
            if hasattr(self.content_object, 'get_absolute_url'):
                self.path = self.content_object.get_absolute_url() or self.path
            if hasattr(self.content_object, 'meta_description'):
                self.description = striptags(self.content_object.meta_description) or self.description
            if hasattr(self.content_object, 'meta_keywords'):
                self.keywords = striptags(self.content_object.meta_keywords) or self.keywords
            if hasattr(self.content_object, 'meta_title'):
                self.title = self.content_object.meta_title or self.title
                # Populate the heading, without overwriting existing data
                self.heading = self.heading or self.content_object.meta_title

            # Populate using other, non-meta fields, but never overwrite existing data
            elif hasattr(self.content_object, 'page_title'):
                self.title = self.title or self.content_object.page_title
                self.heading = self.heading or self.content_object.page_title
            elif hasattr(self.content_object, 'title'):
                self.title = self.title or self.content_object.title
                self.heading = self.heading or self.content_object.title

            return True

    @property
    def category_meta_data(self):
        """ Return the Meta Data instance that is responsible for the entire content type. 
            If this is not applicable, return None.
        """
        if self.content_type_id is not None and self.object_id is not None:
            if not hasattr(self, '_category_meta_data'):
                try:
                    self._category_meta_data = self.__class__._default_manager.get(content_type__id=self.content_type_id, object_id__isnull=True)
                except self.__class__.DoesNotExist:
                    self._category_meta_data = None
            return self._category_meta_data

    @property
    def formatted(self):
        return TemplateMetaData(self)


class ViewMetaData(MetaData):
    """ A subclass of meta data that can be found by searching for the view. """
    view           = SystemViewField(blank=True, null=True, unique=True)

    class Meta:
        verbose_name = u"view metadata"
        verbose_name_plural = u"view metadata"


class TemplateMetaData(dict):
    """ Class to make template access to meta data more convienient.
    """
    title       = property(lambda s: s._get_value('title', DEFAULT_TITLE))
    keywords    = property(lambda s: s._get_value('keywords', DEFAULT_KEYWORDS, tag=True))
    description = property(lambda s: s._get_value('description', DEFAULT_DESCRIPTION, tag=True))
    heading     = property(lambda s: s._get_value('heading'))
    subheading  = property(lambda s: s._get_value('subheading'))
    extra       = property(lambda s: s._get_value('extra'))

    def __init__(self, meta_data, view_meta_data=None):
        self._meta_data = meta_data
        self._view_meta_data = view_meta_data
        self._category_meta_data = None

    def _get_value(self, name, default=None, tag=False):
        """ Retrieves a sensible value and prepares it for display. """
        # Get the raw value from the meta data object
        value = getattr(self._meta_data, name)
        # If no value is found, look in the view meta data
        if not value and self._view_meta_data is not None:
            value = getattr(self._view_meta_data, name)
        # If no value is found, look for a category or a default
        if not value:
            value = self._get_category_value(name) or default or ""
        # If this belongs in a tag, escape quote symbols
        if tag:
            value = value.replace('"', '&#34;')
        # Prevent auto escaping on this value
        return mark_safe(value)

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

    def resolve(self, context):
        if self._view_meta_data is not None:
            for name in ('title', 'keywords', 'description', 'heading', 'subheading', 'extra'):
                setattr(self._view_meta_data, name, _resolve(getattr(self._view_meta_data, name), context_instance=context))

    @property
    def html(self):
        """ Return an html representation of this meta data suitable
            for inclusion in <head>. 
            Note:
              * 'heading' and 'subheading' should not be included.
              * Be careful not to try to get the full html inside this template.
        """
        return mark_safe(render_to_string(TEMPLATE, self.context))

    @property
    def context(self):
        return {CONTEXT_VARIABLE: self}

    def __unicode__(self):
        """ String version of this object is the html output. """
        return self.html


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

#from django.core import urlresolvers
#from django.conf import settings
#def _get_view_callback(request):
#    urlconf = settings.ROOT_URLCONF
#    urlresolvers.set_urlconf(urlconf)
#    resolver = urlresolvers.RegexURLResolver(r'^/', urlconf)
#
#    if hasattr(request, "urlconf"):
#        # Reset url resolver with a custom urlconf.
#        urlconf = request.urlconf
#        urlresolvers.set_urlconf(urlconf)
#        resolver = urlresolvers.RegexURLResolver(r'^/', urlconf)
#
#    return resolver.resolve(request.path_info)[0]


VALID_HEAD_TAGS = "head title base link meta script".split()
def strip_for_head(value):
    """ Strips text from the given html string, leaving only tags.
        This functionality requires BeautifulSoup, nothing will be 
        done otherwise.
    """
    if BeautifulSoup is None:
        return value
    soup = BeautifulSoup(value)
    [ tag.extract() for tag in list(soup) if not (getattr(tag, 'name', None) in VALID_HEAD_TAGS) ]
    return str(soup)


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
            if not md_created: # handle url change
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


