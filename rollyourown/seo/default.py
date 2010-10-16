#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from rollyourown import seo


class DefaultMetaData(seo.MetaData):
    title       = seo.Tag(head=True, max_length=68)
    keywords    = seo.MetaTag()
    description = seo.MetaTag(max_length=155)
    heading     = seo.Tag(name="h1")

    #subheading = seo.Tag(name="h2")
    #extra      = seo.Raw(head=True)
    #example    = seo.Tag(field=models.CharField, max_length=255)
    #example2   = seo.MetaTag(head=True, name="description")

    #og_title       = seo.MetaTag(name="og:title", populate_from="title")
    #og_description = seo.MetaTag(name="og:description", populate_from="description")
    #og_image       = seo.MetaTag(name="og:image", populate_from="get_og_image")
    #og_type        = seo.MetaTag(name="og:type", populate_from="get_og_type", editable=False)
    #og_url         = seo.MetaTag(name="og:url", populate_from="get_absolute_url", editable=False)
    #og_site_name   = seo.MetaTag(name="og:site_name", populate_from=seo.Literal(settings.SITE_NAME), editable=False)
    #og_admins      = seo.MetaTag(name="fb:admins", populate_from=seo.Literal("511258799"), editable=False)
    #og_app_id      = seo.MetaTag(name="fb:app_id", populate_from=seo.Literal("137408292967167"), editable=False)

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

    DEFINITION
    + if "head" is True, tag is automatically included in the head
    + if "name" is included, that is the name of the given tag, otherwise, the field name is used
    + if verbose_name is used, pass on to field (through field_kwargs)
    + if the field argument given, that Django field type is used
    + if editable is set to False, no Django model field is created. The value is always from populate_from
    + if choices is given it is passed onto the field, (expanded if just a list of strings)
    + If help_text used, this is passed onto the field
        + the populate_from of the field is sometimes mentioned automatically in the help_text:
        + if populate_from value is a field name: "If empty, {{ field_name }} will be used"
        + if populate_from value is callable with a short_description attribute: "If empty, {{ short description }} will be used."

    META OPTIONS
    - groups: these elements are grouped together in both the admin and the outputted meta (otherwise ordering is the same as in the definition)
    - use_sites: add a 'site' field to each model. Non-matching sites are removed, null is allowed, meaning all sites match.
    - models: list of models and/or apps which are available for model instance meta data
    - (FUTURE: verbose_name(_plural): this is passed onto Django)
    - HelpText: Help text can be applied in bulk by using a special class, like 'Meta'

    VALUE RESOLUTION
    - if text is missing from a given meta data entry, populate_from is used
    + populate_from is resolved: 
        1) callable
        2) name of field/callable on metadata object
        3) literal value
    - if no text is found, a more general meta data entry is searched for (ordering is Path->ModelInstance->Model->View)

    FORMATTING (write tests for each cose)
    - tags that are not in valid_tags are removed (valid tags can be a space separated string or list, see code for defaults)
    - meta tags are encoded to avoid wayward '"', '&' etc
    - keyword tags are converted to be a comma-separated list

    TEMPLATES (write test for each case)
    - {% get_metadata %} without arguments outputs the head elements
    - {% get_metadata as metadata %} stores the accessor as a variable
    - {% metadata %} outputs all the head elements
    - {% metadata.groupname %} outputs all the elements in given group
    - {% metadata.fieldname %} outputs a single element (full tag)
    - {% metadata.fieldname.value %} outputs only the value from a single element
    - {% metadata.fieldname.field.name %} outputs the element's name etc


USAGE:

    {% load seo %}

    {% get_metadata as metadata %}
    <head>
    {{ metadata }}

    <!-- eg facebook grouped metadata -->
    {{ metadata.facebook }}

    </head>
    <h2>{{ metadata.subtitle }}</h2>


Problems:
    - editable has a different meaning to Django's (can live with that)
    - help_text editing isn't done in Django and can't be turned off
    - max_length is set implicitly, should this be set explicitly? (I can live with this, length is rarely important)


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

    class Meta:
        verbose_name = "Path-based metadata"
        verbose_name_plural = "Path-based metadata"

class DefaultModelMetaDataModel(DefaultMetaDataMode):
    " For model-based metadata "
    path           = models.CharField(max_length=511)
    content_type   = models.ForeignKey(ContentType, null=True, blank=True,
                                        limit_choices_to={'id__in': get_seo_content_types()})
    object_id      = models.PositiveIntegerField(null=True, blank=True, editable=False)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "Model-based metadata"
        verbose_name_plural = "Model-based metadata"


class DefaultViewMetaDataModel(DefaultMetaDataMode):
    " For view-based metadata "
    view = SystemViewField(blank=True, null=True, unique=True)

    class Meta:
        verbose_name = "View-based metadata"
        verbose_name_plural = "View-based metadata"

"""
