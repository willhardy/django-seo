#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import seo


class DefaultMetaData(seo.MetaData):
    title       = seo.Tag(head=True, help_text="This is the meta (page) title, that appears in the title bar.")
    keywords    = seo.MetaTag(help_text="Comma-separated keywords for search engines.")
    description = seo.MetaTag(help_text="A short description, displayed in search results.")
    heading     = seo.Tag(name="h1", help_text="This is the page heading, that appears in the &lt;h1&gt; tag.")

    # Needs to be flexible enough to:
    #   - allow literal values (eg og_app_id)
    #   - allow uneditable values (eg og_app_id)
    #   - allow dynamic defaults for missing values (eg og_description)
    #   - allow choices
    #   - allow callables

    #subheading = seo.Tag(name="h2", help_text="This is the page subheading, that appears near the &lt;h1&gt; tag.")
    #extra      = seo.Raw(head=True, help_text="(advanced) Any additional HTML to be placed verbatim in the &lt;head&gt;")
    #example    = seo.Tag(models.CharField(max_length=255))
    #example2   = seo.MetaTag(head=True, name="description")

    #og_title       = seo.MetaTag(name="og:title", default="{{ title }}")
    #og_description = seo.MetaTag(name="og:description", default="{{ description }}")
    #og_image       = seo.MetaTag(name="og:image", default="{{ content_object.main_image }}")
    #og_type        = seo.MetaTag(name="og:type", default="{{ get_og_type }}")
    #og_url         = seo.MetaTag(name="og:url", default="{{ get_absolute_url }}", editable=False)
    #og_site_name   = seo.MetaTag(name="og:site_name", default="Kogan Technologies", editable=False)
    #og_admins      = seo.MetaTag(name="fb:admins", default="511258799", editable=False)
    #og_app_id      = seo.MetaTag(name="fb:app_id", default="137408292967167", editable=False)

    #def get_og_type(self):
    #    return self.blah

    class Meta:
        verbose_name = "Meta data"
        verbose_name_plural = "Meta data"


""" The Following is then created:

class DefaultMetaDataModel(models.Model):
    title       = models.CharField(max_length=511, default="", blank=True, help_text="This is the meta (page) title, that appears in the title bar.")
    keywords    = models.TextField(default="", blank=True, help_text="Comma-separated keywords for search engines.")
    description = models.TextField(default="", blank=True, help_text="A short description, displayed in search results.")
    heading     = models.CharField(max_length=511, default="", blank=True, help_text="This is the page heading, that appears in the &lt;h1&gt; tag.")

    #extra      = models.TextField(default="", blank=True, help_text="(advanced) Any additional HTML to be placed verbatim in the &lt;head&gt;")
    #subheading = models.CharField(max_length=511, default="", blank=True, help_text="This is the page subheading, that appears near the &lt;h1&gt; tag.")
    #example    = models.CharField(max_length=255)
    #example2   = models.CharField(max_length=511, default="", blank=True)

    #og_title       = models.CharField(max_length=511, default="", blank=True)
    #og_description = models.CharField(max_length=511, default="", blank=True)
    #og_image       = models.CharField(max_length=511, default="", blank=True)
    #og_type        = models.CharField(choices=(("company", "company"),("product", "product")))

    # For model-based metadata
    content_type   = models.ForeignKey(ContentType, null=True, blank=True,
                                        limit_choices_to={'id__in': get_seo_content_types()})
    object_id      = models.PositiveIntegerField(null=True, blank=True, editable=False)
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    # For view-based metadata
    view           = SystemViewField(blank=True, null=True, unique=True)

    class Meta:
        verbose_name = "Meta data"
        verbose_name_plural = "Meta data"


"""
