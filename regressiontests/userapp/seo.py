from rollyourown import seo
from django.db import models


class Coverage(seo.MetaData):
    """ A SEO meta data definition, which should cover all configurable options.
    """
    def get_populate_from1(self):
        return "wxy"

    def get_populate_from2(self):
        return "xyz"
    get_populate_from2.short_description = "Always xyz"

    title        = seo.Tag()
    heading      = seo.Tag(max_length=68, name="hs:tag", verbose_name="tag two", head=True)

    keywords     = seo.MetaTag()
    description  = seo.MetaTag(max_length=155, name="hs:metatag", verbose_name="metatag two")

    raw1         = seo.Raw()
    raw2         = seo.Raw(head=True, verbose_name="raw two", valid_tags=("meta", "title"))

    help_text1   = seo.Tag(help_text="Some help text 1.")
    help_text2   = seo.Tag(populate_from="def")
    help_text3   = seo.Tag(help_text="Some help text 3.", populate_from=get_populate_from1)
    help_text4   = seo.Tag(populate_from=get_populate_from2)

    populate_from1     = seo.Tag(populate_from="get_populate_from1")
    populate_from2     = seo.Tag(populate_from="heading")
    populate_from3     = seo.Tag(populate_from=seo.Literal("efg"))
    populate_from4     = seo.Tag(populate_from="ghi")
    populate_from5     = seo.Tag(populate_from="ghi", editable=False)

    field1       = seo.Tag(field=models.TextField)

    class Meta:
        verbose_name = "Basic Meta datum"
        verbose_name_plural = "Basic Meta data"
        use_sites = False
        groups = { 
            'advanced': ('raw1', 'raw2' ),
            'help_text': ( 'help_text1', 'help_text2', 'help_text3', 'help_text4', )
        }
        seo_models = ('userapp',)

    class HelpText:
        help_text2 = "Updated help text2."


class WithSites(seo.MetaData):
    title        = seo.Tag()

    class Meta:
        use_sites = True
