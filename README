================
Django SEO tools
================

This is a set of SEO tools for Django.
It allows you to associate metadata with:

* absolute paths
* model instances
* model classes
* views

Metadata can be edited in the admin in a centralised place, but also alongside any associated models.

This is however a framework, not an app. You therefore have
complete control over the data you store. 
Here is an example of a definition::

    from rollyourown import seo

    class BasicMetadata(seo.Metadata):
        title          = seo.Tag(max_length=68, head=True)
        keywords       = seo.KeywordTag()
        description    = seo.MetaTag(max_length=155)
        heading        = seo.Tag(name="h1")
        subheading     = seo.Tag(name="h2")
        extra          = seo.Raw(head=True)
    
        # Adding some fields for facebook (opengraph)
        og_title       = seo.MetaTag(name="og:title", populate_from="title", verbose_name="facebook title")
        og_description = seo.MetaTag(name="og:description", populate_from="description", verbose_name='facebook description')

As you can see it is very flexible, but there is much more than this simple example.

The full documentation can be read online at http://django-seo.readthedocs.org/.
