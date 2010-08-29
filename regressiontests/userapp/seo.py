import seo

class Coverage(seo.MetaData):
    """ A SEO meta data definition, which should cover all configurable options.
    """
    tag1         = seo.Tag()
    tag2         = seo.Tag(max_length=68, default="abc", name="hs:tag", verbose_name="tag two", head=True)

    metatag1     = seo.MetaTag()
    metatag2     = seo.MetaTag(max_length=155, default="bcd", name="hs:metatag", verbose_name="metatag two")

    raw1         = seo.Raw()
    raw2         = seo.Raw(head=True, default="cde", verbose_name="raw two", valid_tags=("meta", "title"))

    help_text1   = seo.Tag(help_text="Some help text 1.")
    help_text2   = seo.Tag(help_text="Some help text 2.", default="def")
    help_text3   = seo.Tag(help_text="Some help text 3.", default=get_default1)
    help_text4   = seo.Tag(help_text="Some help text 4.", default=get_default2)

    default1     = seo.Tag(default="get_default1")
    default2     = seo.Tag(default="tag2")
    default3     = seo.Tag(default=seo.Literal("efg"))
    default4     = seo.Tag(default="ghi")
    default5     = seo.Tag(default="ghi", editable=False)

    field1       = seo.Tag(field=models.TextField)

    class Meta:
        verbose_name = "Basic Meta datum"
        verbose_name_plural = "Basic Meta data"
        use_sites = False
        groups = { 
            'advanced': ('raw1', 'raw2' )
            'help_text': ( 'help_text1', 'help_text2', 'help_text3', 'help_text4', )
        }

    def get_default1(self):
        return "wxy"

    def get_default2(self):
        return "xyz"
    get_default2.short_description = "Always xyz"
