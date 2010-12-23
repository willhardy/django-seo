from rollyourown import seo
from django.db import models
from django.contrib.sites.models import Site

site_name = "example.com"

class Coverage(seo.Metadata):
    """ A SEO metadata definition, which should cover all configurable options.
    """
    def get_populate_from1(self, instance):
        return "wxy"

    def get_populate_from2(self, instance):
        return "xyz"
    get_populate_from2.short_description = "Always xyz"

    title        = seo.Tag(populate_from=seo.Literal(site_name), head=True)
    heading      = seo.Tag(max_length=68, name="hs:tag", verbose_name="tag two", head=True)

    keywords     = seo.KeywordTag()
    description  = seo.MetaTag(max_length=155, name="hs:metatag", verbose_name="metatag two")

    raw1         = seo.Raw()
    raw2         = seo.Raw(head=True, verbose_name="raw two", valid_tags=("meta", "title"))

    help_text1   = seo.Tag(help_text="Some help text 1.")
    help_text2   = seo.Tag(populate_from="def")
    help_text3   = seo.Tag(populate_from=get_populate_from1, help_text="Some help text 3.")
    help_text4   = seo.Tag(populate_from=get_populate_from2)
    help_text5   = seo.Tag(populate_from="heading")
    help_text6   = seo.Tag(populate_from="heading", help_text="Some help text 6.")

    populate_from1     = seo.Tag(populate_from="get_populate_from1")
    populate_from2     = seo.Tag(populate_from="heading")
    populate_from3     = seo.Tag(populate_from=seo.Literal("efg"))
    populate_from4     = seo.Tag(populate_from="ghi")
    populate_from5     = seo.Tag(populate_from="ghi", editable=False)
    populate_from6     = seo.Tag(populate_from="keywords")
    populate_from7     = seo.Tag(populate_from=get_populate_from1)

    field1       = seo.Tag(field=models.TextField)

    class Meta:
        verbose_name = "Basic Metadatum"
        verbose_name_plural = "Basic Metadata"
        use_sites = False
        groups = { 
            'advanced': ('raw1', 'raw2' ),
            'help_text': ( 'help_text1', 'help_text2', 'help_text3', 'help_text4', )
        }
        seo_models = ('userapp',)
        seo_views = ('userapp', )

    class HelpText:
        help_text2 = "Updated help text2."


class WithSites(seo.Metadata):
    title        = seo.Tag()

    class Meta:
        use_sites = True

class WithI18n(seo.Metadata):
    title        = seo.Tag()

    class Meta:
        use_i18n = True

class WithRedirect(seo.Metadata):
    title        = seo.Tag()

    class Meta:
        use_redirect = True

class WithRedirectSites(seo.Metadata):
    title        = seo.Tag()

    class Meta:
        use_sites = True
        use_redirect = True

class WithCache(seo.Metadata):
    title    = seo.Tag(head=True, populate_from=seo.Literal("1234"))
    subtitle = seo.Tag(head=True)

    class Meta:
        use_cache = True

class WithCacheSites(seo.Metadata):
    title    = seo.Tag(head=True, populate_from=seo.Literal("1234"))
    subtitle = seo.Tag(head=True)

    class Meta:
        use_cache = True
        use_sites = True

class WithCacheI18n(seo.Metadata):
    title    = seo.Tag(head=True, populate_from=seo.Literal("1234"))
    subtitle = seo.Tag(head=True)

    class Meta:
        use_cache = True
        use_i18n = True

class WithBackends(seo.Metadata):
    title    = seo.Tag()

    class Meta:
        backends = ('view', 'path')
