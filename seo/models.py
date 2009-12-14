# -*- coding: UTF-8 -*-

""" 
    Model definition for django seo app.
    To use this app:
        1. Install the seo directory somewhere in your python path
        2. Add 'seo' to INSTALLED_APPS
        3. If you would like to reference objects, define SEO_MODELS in settings
           as a list of model or app names eg ('flatpages.FlatPage', 'blog',)
        4. Do one or both of the following
          a) Add 'seo.context_processors.seo' to TEMPLATE_CONTEXT_PROCESSORS
             and reference meta_title, meta_description and meta_keywords in 
             your (base) templates
          b) Add 'seo.middleware.MetaDataMiddleware' to MIDDLEWARE and
             make sure meta data isn't already defined in the template.

"""

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from seo.utils import get_seo_models, get_seo_content_types
from django.template.defaultfilters import striptags
from django.utils.safestring import mark_safe
from django.conf import settings

DEFAULT_TITLE = getattr(settings, "SEO_DEFAULT_TITLE", None)
DEFAULT_KEYWORDS = getattr(settings, "SEO_DEFAULT_KEYWORDS", "")
DEFAULT_DESCRIPTION = getattr(settings, "SEO_DEFAULT_DESCRIPTION", "")
if not DEFAULT_TITLE:
    from django.contrib.sites.models import Site
    current_site = Site.objects.get_current()
    DEFAULT_TITLE = current_site.name or current_site.domain

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
    path        = models.CharField(max_length=255, default="", blank=True, unique=True, help_text="Specify the path (URL) for this page (only if no object is linked).")
    title       = models.CharField(max_length=511, default="", blank=True, help_text="This is the meta (page) title, that appears in the title bar.")
    heading     = models.CharField(max_length=511, default="", blank=True, help_text="This is the page heading, that appears in the &lt;h1&gt; tag")
    keywords    = models.TextField(default="", blank=True)
    description = models.TextField(default="", blank=True)
    extra       = models.TextField(default="", blank=True, help_text="(advanced) Any additional HTML to be placed verbatim in the &lt;head&gt;")

    # If the generic foreign key is set, populate the above fields from there
    content_type   = models.ForeignKey(ContentType, null=True, blank=True, editable=False,
                                        limit_choices_to={'id__in': [ct.id for ct in get_seo_content_types()]})
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
        return self.path or "(%s)" % self.title

    def save(self, force_insert=False, force_update=False, update_related=True):
        super(MetaData, self).save(force_insert, force_update)
        if update_related:
            self.update_related_object()

    @property
    def html(self):
        # TODO: Make sure there are no double quotes (") in the content="" attributes
        tags = []
        tags.append(u"<title>%s</title>" % (mark_safe(self.title) or DEFAULT_TITLE))
        tags.append(u'<meta name="keywords" content="%s">' % (mark_safe(striptags(self.keywords)) or DEFAULT_KEYWORDS))
        tags.append(u'<meta name="description" content="%s">' % (mark_safe(striptags(self.description)) or DEFAULT_DESCRIPTION))
        if self.extra:
            tags.append(self.extra)
        return mark_safe("\n".join(tags))

    @property
    def context(self):
        context = {}
        context['meta_title'] = mark_safe(self.title)
        context['meta_keywords'] = mark_safe(striptags(self.keywords))
        context['meta_description'] = mark_safe(striptags(self.description))
        context['meta_heading'] = mark_safe(self.heading)
        context['seo_meta_data'] = self.html
        return context

    def update_related_object(self):
        """ Helps ensure that denormalised data is synchronised. 
            That is, if data is discovered through explicit fields, these are 
        """
        if self.content_object:
            attrs = {}
            # Only populate the fields that are explicity defined
            # TODO: Check for actual fields, not attributes!
            if hasattr(self.content_object, 'meta_description'):
                attrs['meta_description'] = self.description
            if hasattr(self.content_object, 'meta_keywords'):
                attrs['meta_keywords'] = self.keywords
            if hasattr(self.content_object, 'meta_title'):
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
                self.description = self.content_object.meta_description or self.description
            if hasattr(self.content_object, 'meta_keywords'):
                self.keywords = self.content_object.meta_keywords or self.keywords
            if hasattr(self.content_object, 'meta_title'):
                self.title = self.content_object.meta_title or self.title

            # Populate using other, non-meta fields, but never overwrite existing data
            elif hasattr(self.content_object, 'page_title'):
                self.title = self.title or self.content_object.page_title
            elif hasattr(self.content_object, 'title'):
                self.title = self.title or self.content_object.title

            return True

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
    path = instance.get_absolute_url()
    if path:
        try:
            # Look for an existing object with this path
            meta_data = MetaData.objects.get(path=path)
            # If a path is defined, but the content_type and object_id aren't, 
            # then adopt this object
            if not meta_data.content_type:
                meta_data.content_type = content_type
                meta_data.object_id = instance.id
            # If another object has the same path, remove the path.
            # It's harsh, but we need a unique path and will assume the other
            # link is outdated.
            else:
                meta_data.path = None
                meta_data.save()
                # Move on, this isn't out meta_data instance
                meta_data = None
        except MetaData.DoesNotExist:
            pass

    # If the path-based search didn't work, look for (or create) an existing
    # instance linked to this object.
    if not meta_data:
        meta_data, md_created = MetaData.objects.get_or_create(content_type=content_type, object_id=instance.id)

    # Update the MetaData instance with data from the object
    if meta_data.update_from_related_object():
        meta_data.save(update_related=False)


# Connect the models listed in settings to the update callback.
for model in get_seo_models():
    models.signals.post_save.connect(update_callback, sender=model)
