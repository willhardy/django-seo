#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from seo.models import MetaData, ViewMetaData
from userapp.models import Page, Product, Category, NoPath
try:
    import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class LinkedObjects(TestCase):
    """ Checks the flow of data betwee a linked object and its meta data. """

    def setUp(self):

        self.product = Product.objects.create(meta_title="Product Meta Title", 
                                meta_description="Product Meta Description", 
                                meta_keywords="Product Meta Keywords")
        self.product_content_type = ContentType.objects.get_for_model(Product)
        self.product_meta_data = MetaData.objects.get(content_type=self.product_content_type, object_id=self.product.id)

        self.page = Page.objects.create(title=u"Page Title", type="abc")
        self.page_content_type = ContentType.objects.get_for_model(Page)
        self.page_meta_data = MetaData.objects.get(content_type=self.page_content_type, object_id=self.page.id)

        self.category = Category.objects.create()
        self.category_content_type = ContentType.objects.get_for_model(Category)
        self.category_meta_data = MetaData.objects.get(content_type=self.category_content_type, object_id=self.category.id)

    def test_population(self):
        """ Checks that the meta data object is populated with the object's data at the beginning. 
        """
        self.assertEqual(self.product_meta_data.title, "Product Meta Title")
        self.assertEqual(self.product_meta_data.description, "Product Meta Description")
        self.assertEqual(self.product_meta_data.keywords, "Product Meta Keywords")
        self.assertEqual(self.product_meta_data.heading, "Product Meta Title")
        self.assertEqual(self.page_meta_data.title, "Page Title")
        self.assertEqual(self.page_meta_data.heading, "Page Title")
        self.assertEqual(self.category_meta_data.title, "M Category Page Title")

    def test_update(self):
        """ Checks that the meta data object is populated with the object's data when the object is updated.
        """
        # Update the product object
        self.product.meta_title = "New Product Meta Title"
        self.product.meta_description = "New Product Meta Description"
        self.product.meta_keywords = "New Product Meta Keywords"
        self.product.save()

        # Explicit fields are updated.
        product_meta_data = MetaData.objects.get(content_type=self.product_content_type, object_id=self.product.id)
        self.assertEqual(product_meta_data.title, "New Product Meta Title")
        self.assertEqual(product_meta_data.description, "New Product Meta Description")
        self.assertEqual(product_meta_data.keywords, "New Product Meta Keywords")
        self.assertEqual(product_meta_data.heading, "Product Meta Title")

        # Update the page object
        self.page.title = "New Page Title"
        self.page.save()

        # Non explicit fields are not updated.
        page_meta_data = MetaData.objects.get(content_type=self.page_content_type, object_id=self.product.id)
        self.assertEqual(page_meta_data.title, "Page Title")
        self.assertEqual(page_meta_data.heading, "Page Title")

    def test_backport(self):
        """ Checks that changes to the meta data are passed back to 
            denormalised fields on the object. 
        """
        # "meta_title" field is not updated
        self.product_meta_data.title = "New Product Title"
        self.product_meta_data.save()
        product = Product.objects.get(id=self.product.id)
        self.assertEqual(product.meta_title, "New Product Title")

        # "title" field is not updated
        self.page_meta_data.title = "New Page Title"
        self.page_meta_data.save()
        page = Page.objects.get(id=self.page.id)
        self.assertEqual(page.title, "Page Title")

    def test_adoption(self):
        """ Check that an existing meta data object is adopted by a 
            new model instance.
        """
        # Create a meta data object manually
        meta_data = MetaData.objects.create(path="/products/2/", title="Old Title", keywords="Old Keywords")
        self.assertEqual(meta_data.object_id, None)
        num_data = MetaData.objects.all().count()

        # Create new product with the same path as the existing meta data
        product = Product.objects.create(meta_title="New Title")

        # Check that the existing meta data object was adopted
        self.assertEqual(MetaData.objects.all().count(), num_data)
        meta_data = MetaData.objects.get(path="/products/2/")
        self.assertEqual(meta_data.title, "New Title")
        self.assertEqual(meta_data.keywords, "Old Keywords")
        self.assertEqual(meta_data.object_id, 2)

    def test_chaos(self):
        """ Check the crazy scenario where an existing meta data object has the same path. """
        self.product_meta_data.path = '/products/2/'
        self.product_meta_data.save()
        self.assertEqual(self.product_meta_data.object_id, 1)
        product = Product.objects.create(meta_title="New Title")
        # This test will not work if we have the id wrong
        if product.id != 2:
            raise Exception("Test Error: the product ID is not as expected, this test cannot work.")
        product_meta_data = MetaData.objects.get(id=self.product_meta_data.id)
        meta_data = MetaData.objects.get(path="/products/2/")
        self.assertEqual(meta_data.title, u"New Title")
        self.assertEqual(meta_data.keywords, u"")
        self.assertEqual(meta_data.object_id, 2)

    def test_useful_error_messages(self):
        """ Tests that the system gracefully handles a developer error 
            (eg exception in get_absolute_url).
        """
        from django.core.urlresolvers import NoReverseMatch
        try:
            self.page.type = "a type with spaces!" # this causes get_absolute_url() to fail
            self.page.save()
            self.fail("No exception raised on developer error.")
        except NoReverseMatch:
            pass

    def test_missing_meta(self):
        """ Check that no exceptions are raised when the meta data object is missing. """
        try:
            self.page_meta_data.delete()
            self.page.title = "A New Page Title"
            self.page.save()
            MetaData.objects.get(content_type=self.page_content_type, object_id=self.page.id).delete()
            self.page.type = "a-new-type"
            self.page.save()
            MetaData.objects.get(content_type=self.page_content_type, object_id=self.page.id).delete()
            self.page.delete()
        except Exception, e:
            self.fail("Exception raised inappropriately: %r" % e)

    def test_path_change(self):
        """ Check the ability to change the path of meta data. """
        self.page.type = "new-type"
        self.page.save()
        meta_data_1 = MetaData.objects.get(path=self.page.get_absolute_url())
        meta_data_2 = MetaData.objects.get(content_type=self.page_content_type, object_id=self.page.id)
        self.assertEqual(meta_data_1.id, meta_data_2.id)

    def test_delete_object(self):
        """ Tests that an object can be deleted, and the meta data is deleted with it. """
        num_meta_data = MetaData.objects.all().count()
        old_path = self.page.get_absolute_url()
        self.page.delete()
        self.assertEqual(MetaData.objects.all().count(), num_meta_data - 1)
        self.assertEqual(MetaData.objects.filter(path=old_path).count(), 0)

class ContentTypes(TestCase):
    """ A set of unit tests that check the usage of content types. """

    def setUp(self):
        self.page1 = Page.objects.create(title=u"MD Page One Title", type=u"page-one-type", content=u"Page one content.")
        self.page2 = Page.objects.create(type=u"page-two-type", content=u"Page two content.")

        content_type = ContentType.objects.get_for_model(Page)

        self.meta_data1 = MetaData.objects.get(content_type=content_type, object_id=self.page1.id)
        self.meta_data1.keywords = "MD Keywords"
        self.meta_data1.save()
        self.meta_data2 = MetaData.objects.get(content_type=content_type, object_id=self.page2.id)

        self.category_meta_data = MetaData(content_type=content_type, object_id=None)
        self.category_meta_data.title = u"CMD { Title"
        self.category_meta_data.keywords = u"CMD Keywords, {{ page.type }}, more keywords"
        self.category_meta_data.description = u"CMD Description for {{ page }} and {{ page }}"
        self.category_meta_data.save()

        self.context1 = self.meta_data1.formatted
        self.context2 = self.meta_data2.formatted

    def test_direct_data(self):
        """ Check data is used directly when it is given. """
        self.assertEqual(self.context1.title, u'MD Page One Title')
        self.assertEqual(self.context1.keywords, u'MD Keywords')

    def test_category_data(self):
        """ Check that the category data is used when it is missing from the relevant meta data. 
        """
        # The brace is included to check that no error is thrown by an attempted substitution
        self.assertEqual(self.context2.title, u'CMD { Title')

    def test_category_substitution(self):
        """ Check that category data is substituted correctly """
        self.assertEqual(self.context2.keywords, u'CMD Keywords, page-two-type, more keywords')
        self.assertEqual(self.context1.description, u'CMD Description for MD Page One Title and MD Page One Title')
        self.assertEqual(self.context2.description, u'CMD Description for Page two content. and Page two content.')


from django.core.urlresolvers import reverse

class ViewBasedMetaData(TestCase):
    """ A set of unit tests to check the operateion of view selected meta data. """

    def setUp(self):
        self.meta_data = ViewMetaData.objects.create(view="userapp_my_view")
        self.meta_data.title = "MD {{ text }} Title"
        self.meta_data.keywords = "MD {{ text }} Keywords"
        self.meta_data.description = "MD {{ text }} Description"
        self.meta_data.save()

    def test_substitution(self):
        response = self.client.get(reverse('userapp_my_view', args=["abc123"]))
        self.assertContains(response, u'<title>MD abc123 Title</title>')
        self.assertContains(response, u'<meta name="keywords" content="MD abc123 Keywords" />')
        self.assertContains(response, u'<meta name="description" content="MD abc123 Description" />')

    def test_not_request_context(self):
        """ Tests the view meta data on a view that is not a request context. """
        self.meta_data.view = "userapp_my_other_view"
        self.meta_data.save()
        response = self.client.get(reverse('userapp_my_other_view', args=["abc123"]))
        self.assertContains(response, u'<title>example.com</title>')
        self.assertContains(response, u'<meta name="keywords" content="" />')
        self.assertContains(response, u'<meta name="description" content="" />')

    def test_bad_or_old_view(self):
        self.meta_data.view = "this_view_does_not_exist"
        self.meta_data.save()
        response = self.client.get(reverse('userapp_my_view', args=["abc123"]))
        self.assertContains(response, u'<title>example.com</title>')
        self.assertContains(response, u'<meta name="keywords" content="" />')
        self.assertContains(response, u'<meta name="description" content="" />')


class Formatting(TestCase):
    """ A set of simple unit tests that check formatting. """
    def setUp(self):
        self.meta_data = MetaData(
                path        = "/",
                title       = "The <strong>Title</strong>",
                heading     = "The <em>Heading</em>",
                keywords    = 'Some, keywords", with\n other, chars\'',
                description = "A \n description with \" interesting\' chars.",
                extra       = '<meta name="author" content="seo" /><hr /> ' 
                              'No text outside tags please.')
        self.meta_data.save()

        self.context = self.meta_data.formatted
    
    def test_html(self):
        """ Tests html generation is performed correctly.
            Thorough cleaning is done when BeautifulSoup is available.
        """
        if BeautifulSoup:
            assert self.meta_data.formatted.html == """<title>The <strong>Title</strong></title>
<meta name="keywords" content="Some, keywords&#34;, with,  other, chars'" />
<meta name="description" content="A   description with &#34; interesting' chars." />
<meta name="author" content="seo" />
""", "Incorrect html:\n" + self.meta_data.html
        else:
            assert self.meta_data.formatted.html == """<title>The <strong>Title</strong></title>
<meta name="keywords" content="Some, keywords&#34;, with,  other, chars'" />
<meta name="description" content="A   description with &#34; interesting' chars." />
<meta name="author" content="seo" /><hr /> No text outside tags please.
""", "Incorrect html:\n" + self.meta_data.html

    def test_description(self):
        """ Tests the description is cleaned correctly. """
        exp = "A   description with &#34; interesting' chars."
        self.assertEqual(self.context.description, exp)

    def test_keywords(self):
        """ Tests keywords are cleaned correctly. """
        exp = "Some, keywords&#34;, with,  other, chars'"
        self.assertEqual(self.context.keywords, exp)

    def test_title(self):
        """ Tests the title is cleaned correctly. """
        exp = 'The <strong>Title</strong>'
        self.assertEqual(self.context.title, exp)

    def test_heading(self):
        """ Tests the heading is cleaned correctly. """
        exp = 'The <em>Heading</em>'
        self.assertEqual(self.context.heading, exp)

    def test_extra(self):
        """ Tests the extras attribute is cleaned correctly. 
            Thorough cleaning is done when BeautifulSoup is available.
        """
        if BeautifulSoup:
            exp = '<meta name="author" content="seo" />'
        else:
            exp = ('<meta name="author" content="seo" /><hr />'
                  ' No text outside tags please.')
        self.assertEqual(self.context.extra, exp)


class Random(TestCase):
    """ A collection of random tests for various isolated features. """

    def setUp(self):
        self.page = Page.objects.create(type="abc")
        self.content_type = ContentType.objects.get_for_model(Page)
        self.meta_data = MetaData.objects.get(content_type=self.content_type,
                                                    object_id=self.page.id)
        self.context = self.meta_data.formatted

    def test_default_fallback(self):
        """ Tests the ability to use the current Site name as a default 
            fallback. 
        """
        from django.contrib.sites.models import Site
        site = Site.objects.get_current()
        self.assertEqual(site.name, self.context.title)

    def test_missing_category_meta_data(self):
        " Checks that lookups work where the category meta data is  missing "
        try:
            self.context.title
        except MetaData.DoesNotExist:
            self.fail("MetaData.DoesNotExist raised inappropriately.")

    def test_unicode_representation(self):
        " Checks the unicode representation of a MetaData object. "
        self.page.title = "How to recognise this page"
        self.page.save()
        meta_data = MetaData.objects.get(id=self.meta_data.id)
        self.assertEqual(unicode(meta_data), self.page.title)

    def test_get_absolute_url(self):
        " Checks the get_absolute_url() method of a MetaData object. "
        self.assertEqual(self.meta_data.get_absolute_url(), self.page.get_absolute_url())

    def test_missing_path(self):
        " Checks that a model with a missing path is gracefully ignored. "
        num_meta_data = MetaData.objects.all().count()
        try:
            no_path = NoPath.objects.create()
        except Exception, e:
            self.fail("Exception inappropriately raised: %r" % e)
        new_num_meta_data = MetaData.objects.all().count()
        self.assertEqual(num_meta_data, new_num_meta_data)

    def test_contenttypes_admin(self):
        """ Checks the custom field for the ViewMetaData admin works correctly. """
        from seo.admin import MetaDataAdmin
        from django.http import HttpRequest
        from django.contrib.admin import site
        request = HttpRequest()
        form = MetaDataAdmin(MetaData, site).get_form(request)()
        assert 'site</option>' not in form.as_table(), form.as_table()

    def test_view_admin(self):
        """ Checks the custom field for the ViewMetaData admin works correctly. """
        from seo.admin import ViewMetaDataAdmin
        from django.http import HttpRequest
        from django.contrib.admin import site
        request = HttpRequest()
        form = ViewMetaDataAdmin(ViewMetaData, site).get_form(request)()
        assert '<option value="userapp_my_view">userapp my view</option>' in form.as_table(), form.as_table()

    def test_clean_extra(self):
        """ Checks that extra head data is cleaned. """
        from seo.admin import MetaDataForm
        extra = u"<title>My Title</title><link/>And them some<link/>"
        form = MetaDataForm(instance=self.meta_data, data={'extra': extra })
        assert not form.is_valid(), "Form should be rejected."

    def test_seo_content_types(self):
        """ Checks the creation of choices for the SEO content types. """
