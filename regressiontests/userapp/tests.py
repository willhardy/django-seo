#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from userapp.models import Page, Product, Category, NoPath
from userapp.seo import Coverage
from rollyourown.seo import get_meta_data
try:
    import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class ModelInstanceMetaData(TestCase):
    """ Checks the flow of data betwee a linked object and its meta data. """

    def setUp(self):

        self.product = Product(meta_title="Product Meta Title", 
                                meta_description="Product Meta Description", 
                                meta_keywords="Product Meta Keywords")
        
        self.product.save()
        self.product_content_type = ContentType.objects.get_for_model(Product)
        self.product_meta_data = Coverage.ModelInstanceMetaData.objects.get(content_type=self.product_content_type, object_id=self.product.id)

        self.page = Page.objects.create(title=u"Page Title", type="abc")
        self.page_content_type = ContentType.objects.get_for_model(Page)
        self.page_meta_data = Coverage.ModelInstanceMetaData.objects.get(content_type=self.page_content_type, object_id=self.page.id)

        self.category = Category.objects.create()
        self.category_content_type = ContentType.objects.get_for_model(Category)
        self.category_meta_data = Coverage.ModelInstanceMetaData.objects.get(content_type=self.category_content_type, object_id=self.category.id)

    def test_path_conflict(self):
        """ Check the crazy scenario where an existing meta data object has the same path. """
        old_path = self.product_meta_data.path
        self.product_meta_data.path = '/products/2/'
        self.product_meta_data.save()
        self.assertEqual(self.product_meta_data.object_id, 1)

        # Create a new product that will take the same path
        product = Product.objects.create(meta_title="New Title")

        # This test will not work if we have the id wrong
        if product.id != 2:
            raise Exception("Test Error: the product ID is not as expected, this test cannot work.")

        # Check that the existing path was corrected
        product_meta_data = Coverage.ModelInstanceMetaData.objects.get(id=self.product_meta_data.id)
        self.assertEqual(old_path, product_meta_data.path)

        # Check the new data is available under the correct path
        meta_data = get_meta_data(path="/products/2/")
        self.assertEqual(meta_data.title, u"New Title")
        self.assertEqual(meta_data.keywords, u"")

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
            Coverage.ModelInstanceMetaData.objects.get(content_type=self.page_content_type, object_id=self.page.id).delete()
            self.page.type = "a-new-type"
            self.page.save()
            Coverage.ModelInstanceMetaData.objects.get(content_type=self.page_content_type, object_id=self.page.id).delete()
            self.page.delete()
        except Exception, e:
            self.fail("Exception raised inappropriately: %r" % e)

    def test_path_change(self):
        """ Check the ability to change the path of meta data. """
        self.page.type = "new-type"
        self.page.save()
        meta_data_1 = Coverage.ModelInstanceMetaData.objects.get(path=self.page.get_absolute_url())
        meta_data_2 = Coverage.ModelInstanceMetaData.objects.get(content_type=self.page_content_type, object_id=self.page.id)
        self.assertEqual(meta_data_1.id, meta_data_2.id)

    def test_delete_object(self):
        """ Tests that an object can be deleted, and the meta data is deleted with it. """
        num_meta_data = Coverage.ModelInstanceMetaData.objects.all().count()
        old_path = self.page.get_absolute_url()
        self.page.delete()
        self.assertEqual(Coverage.ModelInstanceMetaData.objects.all().count(), num_meta_data - 1)
        self.assertEqual(Coverage.ModelInstanceMetaData.objects.filter(path=old_path).count(), 0)


class ModelMetaData(TestCase):
    """ A set of unit tests that check the usage of content types. """

    def setUp(self):
        self.page1 = Page.objects.create(title=u"MD Page One Title", type=u"page-one-type", content=u"Page one content.")
        self.page2 = Page.objects.create(type=u"page-two-type", content=u"Page two content.")

        content_type = ContentType.objects.get_for_model(Page)

        self.meta_data1 = Coverage.ModelInstanceMetaData.objects.get(content_type=content_type, object_id=self.page1.id)
        self.meta_data1.keywords = "MD Keywords"
        self.meta_data1.save()
        self.meta_data2 = Coverage.ModelInstanceMetaData.objects.get(content_type=content_type, object_id=self.page2.id)

        self.category_meta_data = Coverage.ModelMetaData(content_type=content_type)
        self.category_meta_data.title = u"CMD { Title"
        self.category_meta_data.keywords = u"CMD Keywords, {{ page.type }}, more keywords"
        self.category_meta_data.description = u"CMD Description for {{ page }} and {{ page }}"
        self.category_meta_data.save()

        self.context1 = get_meta_data(path=self.page1.get_absolute_url())
        self.context2 = get_meta_data(path=self.page2.get_absolute_url())

    def test_direct_data(self):
        """ Check data is used directly when it is given. """
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

class ViewMetaData(TestCase):
    """ A set of unit tests to check the operateion of view selected meta data. """

    def setUp(self):
        self.meta_data = Coverage.ViewMetaData.objects.create(view="userapp_my_view")
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
        meta_data = Coverage.PathMetaData(
                path        = "/",
                title       = "The <strong>Title</strong>",
                heading     = "The <em>Heading</em>",
                keywords    = 'Some, keywords", with\n other, chars\'',
                description = "A \n description with \" interesting\' chars.",
                raw1        = '<meta name="author" content="seo" /><hr /> ' 
                              'No text outside tags please.',
                raw2        = '<meta name="author" content="seo" />'
                              '<script>make_chaos();</script>')
        meta_data.save()

        self.meta_data = get_meta_data(path="/")
    
    def test_html(self):
        """ Tests html generation is performed correctly.
            Thorough cleaning is done when BeautifulSoup is available.
        """
        if BeautifulSoup:
            assert unicode(self.meta_data) == """<title>The <strong>Title</strong></title>
<meta name="keywords" content="Some, keywords&#34;, with,  other, chars'" />
<meta name="hs:tag" content="A   description with &#34; interesting' chars." />
<meta name="author" content="seo" />
""", "Incorrect html:\n" + unicode(self.meta_data)
        else:
            assert unicode(self.meta_data) == """<title>The <strong>Title</strong></title>
<meta name="keywords" content="Some, keywords&#34;, with,  other, chars'" />
<meta name="hs:tag" content="A   description with &#34; interesting' chars." />
<meta name="author" content="seo" /><hr /> No text outside tags please.
""", "Incorrect html:\n" + unicode(self.meta_data)

    def test_description(self):
        """ Tests the tag2 is cleaned correctly. """
        exp = "A   description with &#34; interesting' chars."
        self.assertEqual(self.meta_data.description.value, exp)
        exp = '<meta name="hs:metatag" content="%s" />' % exp
        self.assertEqual(unicode(self.meta_data.description), exp)

    def test_keywords(self):
        """ Tests keywords are cleaned correctly. """
        # TODO: Add a "KeywordMetaTagField" that converts "\n" to "," 
        # and has useful admin features
        #exp = "Some, keywords&#34;, with,  other, chars'"
        exp = "Some, keywords&#34;, with  other, chars'"
        self.assertEqual(self.meta_data.keywords.value, exp)
        exp = '<meta name="keywords" content="%s" />' % exp
        self.assertEqual(unicode(self.meta_data.keywords), exp)

    def test_title(self):
        """ Tests the title is cleaned correctly. """
        exp = 'The <strong>Title</strong>'
        self.assertEqual(self.meta_data.title.value, exp)
        exp = '<meta name="title" content="%s" />' % exp
        self.assertEqual(unicode(self.meta_data.title), exp)

    def test_heading(self):
        """ Tests the heading is cleaned correctly. """
        exp = 'The <em>Heading</em>'
        self.assertEqual(self.meta_data.heading.value, exp)
        exp = '<meta name="hs:tag" content="%s" />' % exp
        self.assertEqual(unicode(self.meta_data.heading), exp)

    def test_raw1(self):
        """ Tests the extras attribute is cleaned correctly. 
            Thorough cleaning is done when BeautifulSoup is available.
        """
        if BeautifulSoup:
            exp = '<meta name="author" content="seo" />'
        else:
            exp = ('<meta name="author" content="seo" /><hr />'
                  ' No text outside tags please.')
        self.assertEqual(self.meta_data.raw1.value, exp)
        self.assertEqual(unicode(self.meta_data.raw1), exp)

    def test_raw2(self):
        """ Tests the extras attribute is cleaned correctly. 
            Thorough cleaning is done when BeautifulSoup is available.
        """
        if BeautifulSoup:
            exp = '<meta name="author" content="seo" />'
        else:
            exp = ('<meta name="author" content="seo" /><script>make_chaos();</script>')
        self.assertEqual(self.meta_data.raw1.value, exp)
        self.assertEqual(unicode(self.meta_data.raw1), exp)


class Random(TestCase):
    """ A collection of random tests for various isolated features. """

    def setUp(self):
        self.page = Page.objects.create(type="abc")
        self.content_type = ContentType.objects.get_for_model(Page)
        self.meta_data = Coverage.ModelInstanceMetaData.objects.get(content_type=self.content_type,
                                                    object_id=self.page.id)
        self.context = get_meta_data(path=self.meta_data.path)

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
        except Coverage.ModelInstanceMetaData.DoesNotExist:
            self.fail("MetaData.DoesNotExist raised inappropriately.")

    def test_missing_path(self):
        " Checks that a model with a missing path is gracefully ignored. "
        num_meta_data = Coverage.ModelInstanceMetaData.objects.all().count()
        try:
            no_path = NoPath.objects.create()
        except Exception, e:
            self.fail("Exception inappropriately raised: %r" % e)
        new_num_meta_data = Coverage.ModelInstanceMetaData.objects.all().count()
        self.assertEqual(num_meta_data, new_num_meta_data)

    def test_contenttypes_admin(self):
        """ Checks the custom field for the ViewMetaData admin works correctly. """
        from rollyourown.seo.admin import MetaDataAdmin
        from django.http import HttpRequest
        from django.contrib.admin import site
        request = HttpRequest()
        form = MetaDataAdmin(Coverage.ViewMetaData, site).get_form(request)()
        assert 'site</option>' not in form.as_table(), form.as_table()

    def test_view_admin(self):
        """ Checks the custom field for the ViewMetaData admin works correctly. """
        from rollyourown.seo.admin import ViewMetaDataAdmin
        from django.http import HttpRequest
        from django.contrib.admin import site
        request = HttpRequest()
        form = ViewMetaDataAdmin(Coverage.ViewMetaData, site).get_form(request)()
        assert '<option value="userapp_my_view">userapp my view</option>' in form.as_table(), form.as_table()

    def test_clean_extra(self):
        """ Checks that extra head data is cleaned. """
        from rollyourown.seo.admin import MetaDataForm
        extra = u"<title>My Title</title><link/>And them some<link/>"
        form = MetaDataForm(instance=self.meta_data, data={'extra': extra })
        assert not form.is_valid(), "Form should be rejected."

    def test_seo_content_types(self):
        """ Checks the creation of choices for the SEO content types. """
