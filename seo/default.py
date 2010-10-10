#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import seo


class DefaultMetaData(seo.MetaData):
    title       = seo.Tag(head=True, max_length=68)
    keywords    = seo.MetaTag()
    description = seo.MetaTag(max_length=155)
    heading     = seo.Tag(name="h1")

    #subheading = seo.Tag(name="h2")
    #extra      = seo.Raw(head=True)
    #example    = seo.Tag(field=models.CharField, max_length=255)
    #example2   = seo.MetaTag(head=True, name="description")

    #og_title       = seo.MetaTag(name="og:title", default="title")
    #og_description = seo.MetaTag(name="og:description", default="description")
    #og_image       = seo.MetaTag(name="og:image", default="get_og_image")
    #og_type        = seo.MetaTag(name="og:type", default="get_og_type", editable=False)
    #og_url         = seo.MetaTag(name="og:url", default="get_absolute_url", editable=False)
    #og_site_name   = seo.MetaTag(name="og:site_name", default=seo.Literal(settings.SITE_NAME), editable=False)
    #og_admins      = seo.MetaTag(name="fb:admins", default=seo.Literal("511258799"), editable=False)
    #og_app_id      = seo.MetaTag(name="fb:app_id", default=seo.Literal("137408292967167"), editable=False)

    #def get_og_type(self):
    #    if self.model_instance is not None and self.model_instance.__class__.__name__ == 'Product':
    #        return 'product'
    #    return 'website'

    #def get_og_image(self):
    #    return self.model_instance.main_image
    #get_og_type.short_description = "main image from linked product"

    #def get_blah(self):
    #    return self.view

    class Meta:
        verbose_name = "Meta data"
        verbose_name_plural = "Meta data"
        use_sites = False
        #groups = { 
        #    'advanced': ('extra',)
        #    'facebook': ('og_title', 'og_description', 'og_image', 'og_type', 'og_url', 'og_site_name', 'og_admins', 'og_app_id')
        #}

    class HelpText:
        title       = "This is the meta (page) title, that appears in the title bar."
        keywords    = "Comma-separated keywords for search engines."
        description = "A short description, displayed in search results."
        heading     = "This is the page heading, that appears in the &lt;h1&gt; tag."

        #subheading = "This is the page subheading, that appears near the &lt;h2&gt; tag."
        #extra      = "(advanced) Any additional HTML to be placed verbatim in the &lt;head&gt;"
        #og_title   = "Title for facebook"


""" The Following is then created:

    - if "head" is True, tag is automatically included in the head
    - if "name" is included, that is the name of the given tag, otherwise, the field name is used
    - if verbose_name is used, pass on to field
    - if the first argument is a field, that is used (and expanded?)
    - editable is not stored in the model, it is always the default value
    - if choices is given it is passed onto the field, (expanded if just a list of strings)
    - if sites is given in Meta, add a 'site' field.
    - default is resolved: 
        1) callable
        2) name of field/callable on metadata object
        3) literal value
    - If help_text used, this is passed onto the field
        - the default value of the field is sometimes mentioned automatically in the help_text:
        - if default value is field: "If empty, {{ field_name }} will be used"
        - if default value is callable with a short_description attribute: "If empty, {{ short description }} will be used."
    - If groups is mentioned in Meta, these elements are grouped together in both the admin and the outputted meta (otherwise ordering is the same as in the definition)


Problems:
    - editable has a different meaning to Django's
    - default has a different meaning to Django's
    - help_text editing isn't done in Django and can't be turned off
    - max_length is set implicitly, should this be set explicitly?


class DefaultMetaDataModel(models.Model):
    title       = models.CharField(max_length=68, default="", blank=True, help_text="This is the meta (page) title, that appears in the title bar.")
    keywords    = models.CharField(max_length=511, default="", blank=True, help_text="Comma-separated keywords for search engines.")
    description = models.CharField(max_length=155, default="", blank=True, help_text="A short description, displayed in search results.")
    heading     = models.CharField(max_length=511, default="", blank=True, help_text="This is the page heading, that appears in the &lt;h1&gt; tag.")

    #extra      = models.TextField(default="", blank=True, help_text="(advanced) Any additional HTML to be placed verbatim in the &lt;head&gt;")
    #subheading = models.CharField(max_length=511, default="", blank=True, help_text="This is the page subheading, that appears near the &lt;h1&gt; tag.")
    #example    = models.CharField(max_length=255)
    #example2   = models.CharField(max_length=511, default="", blank=True)

    #og_title       = models.CharField(max_length=511, default="", blank=True)
    #og_description = models.CharField(max_length=511, default="", blank=True)
    #og_image       = models.CharField(max_length=511, default="", blank=True)
    #og_type        = models.CharField(choices=(("company", "company"),("product", "product")))

    class Meta:
        verbose_name = "Meta data"
        verbose_name_plural = "Meta data"
        abstract = True


class DefaultPathMetaDataModel(DefaultMetaDataMode):
    " For path-based metadata "
    path = models.CharField(max_length=511)


class DefaultModelMetaDataModel(DefaultMetaDataMode):
    " For model-based metadata "
    path           = models.CharField(max_length=511)
    content_type   = models.ForeignKey(ContentType, null=True, blank=True,
                                        limit_choices_to={'id__in': get_seo_content_types()})
    object_id      = models.PositiveIntegerField(null=True, blank=True, editable=False)
    content_object = generic.GenericForeignKey('content_type', 'object_id')


class DefaultViewMetaDataModel(DefaultMetaDataMode):
    " For view-based metadata "
    view = SystemViewField(blank=True, null=True, unique=True)

"""
