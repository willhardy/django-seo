#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Test suite for SEO framework.

    It is divided into 7 sections:

    * Data selection (Unit tests)
    * Value resolution (Unit tests)
    * Formatting (Unit tests)
    * Definition (System tests)
    * Meta options (System tests)
    * Templates (System tests)
    * Random (series of various uncategorised tests)

    TESTS TO WRITE: 
        - Meta.seo_views: views in list are limited to the given views/apps
        - Meta.seo_models: models in list are limited to the given models/apps
        - valid_tags given as a string
        - Meta.seo_models = appname.modelname (ie with a dot)
        - south compatibility (changing a definition)

        + if "head" is True, tag is automatically included in the head, if "false" then no
        + if "name" is included, that is the name of the given tag, otherwise, the field name is used
        + if verbose_name is used, pass on to field (through field_kwargs)
        + if the field argument given, that Django field type is used (NB default field argument incompatibility?)
        + if editable is set to False, no Django model field is created. The value is always from populate_from
        + if choices is given it is passed onto the field, (expanded if just a list of strings)

        + groups: these elements are grouped together in the admin and can be output together in the template
        + use_sites: add a 'site' field to each model. Non-matching sites are removed, null is allowed, meaning all sites match.
        + sites conflicting sites, when two entries exist for different sites, the explicit (local) one wins. (Even better: both are used, in the appropriate order)
        + models: list of models and/or apps which are available for model instance meta data
        - verbose_name(_plural): this is passed onto Django
        + HelpText: Help text can be applied in bulk by using a special class, like 'Meta'

        - Caching
            - meta data lookups are avoided by caching previous rendering for certain amount of time
            - caching with respect to language and site?

"""
import logging
import StringIO

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.contrib.redirects.models import Redirect
from django.conf import settings
from django.db import IntegrityError
from django.core.handlers.wsgi import WSGIRequest
from django.template import Template, RequestContext, TemplateSyntaxError

from rollyourown.seo import get_meta_data as seo_get_meta_data
from rollyourown.seo.base import registry
from userapp.models import Page, Product, Category, NoPath
from userapp.seo import Coverage, WithSites, WithI18n, WithRedirect, WithRedirectSites


def get_meta_data(path):
    return seo_get_meta_data(path, name="Coverage")


class DataSelection(TestCase):
    """ Data selection (unit tests). Test how meta_data objects are discovered.
    """

    def setUp(self):
        # Model instance meta data
        self.product = Product.objects.create()
        self.product_content_type = ContentType.objects.get_for_model(Product)
        # NB if signals aren't working, the following will fail.
        self.product_meta_data = Coverage.ModelInstanceMetaData.objects.get(_content_type=self.product_content_type, _object_id=self.product.id)
        self.product_meta_data.title="ModelInstance title"
        self.product_meta_data.keywords="ModelInstance keywords"
        self.product_meta_data.save()

        self.page = Page.objects.create(title=u"Page Title", type="abc")
        self.page_content_type = ContentType.objects.get_for_model(Page)
        self.page_meta_data = Coverage.ModelInstanceMetaData.objects.get(_content_type=self.page_content_type, _object_id=self.page.id)
        self.page_meta_data.title="Page title"
        self.page_meta_data.keywords="Page keywords"
        self.page_meta_data.save()

        # Model meta data
        self.model_meta_data = Coverage.ModelMetaData.objects.create(_content_type=self.product_content_type, title="Model title", keywords="Model keywords")

        # Path meta data
        self.path_meta_data = Coverage.PathMetaData.objects.create(_path="/path/", title="Path title", keywords="Path keywords")

        # View meta data
        self.view_meta_data = Coverage.ViewMetaData.objects.create(_view="userapp_my_view", title="View title", keywords="View keywords")

    def test_path(self):
        """ Checks that a direct path listing is always found first. """
        path = self.product.get_absolute_url()
        self.assertNotEqual(get_meta_data(path).title.value, 'Path title')
        self.assertEqual(get_meta_data(path).title.value, 'ModelInstance title')
        self.path_meta_data._path = path
        self.path_meta_data.save()
        self.assertEqual(get_meta_data(path).title.value, 'Path title')

    def test_model_instance(self):
        # With no matching instances, the default should be used
        page = Page(title="Title", type="newpage")
        path = page.get_absolute_url()
        self.assertEqual(get_meta_data(path).title.value, "example.com")

        # Check that a new metadata instance is created
        old_count = Coverage.ModelInstanceMetaData.objects.all().count()
        page.save()
        new_count = Coverage.ModelInstanceMetaData.objects.all().count()
        self.assertEqual(new_count, old_count+1)

        # Check that the correct data is loaded
        assert 'New Page title' not in unicode(get_meta_data(path).title)
        Coverage.ModelInstanceMetaData.objects.filter(_content_type=self.page_content_type, _object_id=page.id).update(title="New Page title")
        self.assertEqual(get_meta_data(path).title.value, 'New Page title')

    def test_model(self):
        path = self.product.get_absolute_url()

        # Model meta data only works if there is no instance meta data
        self.assertEqual(get_meta_data(path).title.value, 'ModelInstance title')
        self.assertEqual(get_meta_data(path).keywords.value, 'ModelInstance keywords')

        # Remove the instance meta data
        self.product_meta_data.keywords = ''
        self.product_meta_data.save()

        self.assertEqual(get_meta_data(path).keywords.value, 'Model keywords')

    def test_view(self):
        path = '/my/view/text/'
        path_meta_data = Coverage.PathMetaData.objects.create(_path=path, title="Path title")
        self.assertEqual(get_meta_data(path).title.value, 'Path title')
        path_meta_data.delete()
        self.assertEqual(get_meta_data(path).title.value, 'View title')

    def test_sites(self):
        """ Tests the django.contrib.sites support.
            A separate meta data definition is used, WithSites, which has turned on sites support.
        """
        path = "/abc/"
        site = Site.objects.get_current()
        path_meta_data = WithSites.PathMetaData.objects.create(_site=site, title="Site Path title", _path=path)
        self.assertEqual(seo_get_meta_data(path, name="WithSites").title.value, 'Site Path title')
        # Meta data with site=null should work
        path_meta_data._site_id = None
        path_meta_data.save()
        self.assertEqual(seo_get_meta_data(path, name="WithSites").title.value, 'Site Path title')
        # Meta data with an explicitly wrong site should not work
        path_meta_data._site_id = site.id + 1
        path_meta_data.save()
        self.assertEqual(seo_get_meta_data(path, name="WithSites").title.value, None)

    def test_i18n(self):
        """ Tests the i18n support, allowing a language to be associated with meta data entries.
        """
        path = "/abc/"
        language = 'de'
        path_meta_data = WithI18n.PathMetaData.objects.create(_language='de', title="German Path title", _path=path)
        self.assertEqual(seo_get_meta_data(path, name="WithI18n", language="de").title.value, 'German Path title')
        # Meta data with an explicitly wrong site should not work
        path_meta_data._language = "en"
        path_meta_data.save()
        self.assertEqual(seo_get_meta_data(path, name="WithI18n", language="de").title.value, None)

    def test_redirect(self):
        """ Tests django.contrib.redirect support, automatically adding redirects for new paths.
        """
        old_path = "/abc/"
        new_path = "/new-path/"

        # Check that the redirect doesn't already exist
        self.assertEqual(Redirect.objects.filter(old_path=old_path, new_path=new_path).count(), 0)

        path_meta_data = WithRedirect.PathMetaData.objects.create(title="A Path title", _path=old_path)
        self.assertEqual(seo_get_meta_data(old_path, name="WithRedirect").title.value, 'A Path title')

        # Rename the path
        path_meta_data._path = new_path
        path_meta_data.save()
        self.assertEqual(seo_get_meta_data(old_path, name="WithRedirect").title.value, None)
        self.assertEqual(seo_get_meta_data(new_path, name="WithRedirect").title.value, 'A Path title')

        # Check that a redirect was created
        self.assertEqual(Redirect.objects.filter(old_path=old_path, new_path=new_path).count(), 1)

    def test_redirect_with_sites(self):
        """ Tests django.contrib.redirect support, automatically adding redirects for new paths.
        """
        old_path = "/abc/"
        new_path = "/new-path/"
        site = Site.objects.get_current()

        # Check that the redirect doesn't already exist
        self.assertEqual(Redirect.objects.filter(old_path=old_path, new_path=new_path, site=site).count(), 0)

        path_meta_data = WithRedirectSites.PathMetaData.objects.create(title="A Path title", _path=old_path, _site=site)
        self.assertEqual(seo_get_meta_data(old_path, name="WithRedirectSites").title.value, 'A Path title')

        # Rename the path
        path_meta_data._path = new_path
        path_meta_data.save()
        self.assertEqual(seo_get_meta_data(old_path, name="WithRedirectSites").title.value, None)
        self.assertEqual(seo_get_meta_data(new_path, name="WithRedirectSites").title.value, 'A Path title')

        # Check that a redirect was created
        self.assertEqual(Redirect.objects.filter(old_path=old_path, new_path=new_path, site=site).count(), 1)

    def test_missing_value(self):
        """ Checks that nothing breaks when no value could be found. 
            The value should be None, the output blank (if that is appropriate for the field).
        """
        path = "/abc/"
        self.assertEqual(seo_get_meta_data(path, name="WithSites").title.value, None)
        self.assertEqual(unicode(seo_get_meta_data(path, name="WithSites").title), "")

    def test_path_conflict(self):
        """ Check the crazy scenario where an existing meta data object has the same path. """
        old_path = self.product_meta_data._path
        self.product_meta_data._path = '/products/2/'
        self.product_meta_data.save()
        self.assertEqual(self.product_meta_data._object_id, 1)

        # Create a new product that will take the same path
        new_product = Product.objects.create()
        Coverage.ModelInstanceMetaData.objects.filter(_content_type=self.product_content_type, _object_id=new_product.id).update(title="New Title")

        # This test will not work if we have the id wrong
        if new_product.id != 2:
            raise Exception("Test Error: the product ID is not as expected, this test cannot work.")

        # Check that the existing path was corrected
        product_meta_data = Coverage.ModelInstanceMetaData.objects.get(id=self.product_meta_data.id)
        self.assertEqual(old_path, product_meta_data._path)

        # Check the new data is available under the correct path
        meta_data = get_meta_data(path="/products/2/")
        self.assertEqual(meta_data.title.value, u"New Title")

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
            Coverage.ModelInstanceMetaData.objects.get(_content_type=self.page_content_type, _object_id=self.page.id).delete()
            self.page.type = "a-new-type"
            self.page.save()
            Coverage.ModelInstanceMetaData.objects.get(_content_type=self.page_content_type, _object_id=self.page.id).delete()
            self.page.delete()
        except Exception, e:
            self.fail("Exception raised inappropriately: %r" % e)

    def test_path_change(self):
        """ Check the ability to change the path of meta data. """
        self.page.type = "new-type"
        self.page.save()
        meta_data_1 = Coverage.ModelInstanceMetaData.objects.get(_path=self.page.get_absolute_url())
        meta_data_2 = Coverage.ModelInstanceMetaData.objects.get(_content_type=self.page_content_type, _object_id=self.page.id)
        self.assertEqual(meta_data_1.id, meta_data_2.id)

        self.assertEqual(get_meta_data(path=self.page.get_absolute_url()).title.value, 'Page title')

    def test_delete_object(self):
        """ Tests that an object can be deleted, and the meta data is deleted with it. """
        num_meta_data = Coverage.ModelInstanceMetaData.objects.all().count()
        old_path = self.page.get_absolute_url()
        self.page.delete()
        self.assertEqual(Coverage.ModelInstanceMetaData.objects.all().count(), num_meta_data - 1)
        self.assertEqual(Coverage.ModelInstanceMetaData.objects.filter(_path=old_path).count(), 0)

    def test_group(self):
        """ Checks that groups can be accessed directly. """
        path = self.path_meta_data._path
        self.path_meta_data.raw1 = "<title>Raw 1</title>"
        self.path_meta_data.raw2 = "<title>Raw 1</title>"
        self.path_meta_data.help_text1 = "Help Text 1"
        self.path_meta_data.help_text3 = "Help Text 3"
        self.path_meta_data.help_text4 = "Help Text 4"
        self.path_meta_data.save()

        self.assertEqual(get_meta_data(path).advanced, u'<title>Raw 1</title>\n<title>Raw 1</title>')
        self.assertEqual(get_meta_data(path).help_text, u'''<help_text1>Help Text 1</help_text1>

<help_text3>Help Text 3</help_text3>
<help_text4>Help Text 4</help_text4>''')

    def test_wrong_name(self):
        """ Missing attribute should raise an AttributeError. """
        path = self.path_meta_data._path
        meta_data = get_meta_data(path)
        try:
            meta_data.this_does_not_exist
        except AttributeError:
            pass
        else:
            self.fail("AttributeError should be raised on missing FormattedMetaData attribute.")

class ValueResolution(TestCase):
    """ Value resolution (unit tests).
    """
    def setUp(self):
        self.page1 = Page.objects.create(title=u"MD Page One Title", type=u"page-one-type", content=u"Page one content.")
        self.page2 = Page.objects.create(type=u"page-two-type", content=u"Page two content.")

        self.page_content_type = ContentType.objects.get_for_model(Page)

        self.meta_data1 = Coverage.ModelInstanceMetaData.objects.get(_content_type=self.page_content_type, _object_id=self.page1.id)
        self.meta_data1.keywords = "MD Keywords"
        self.meta_data1.save()
        self.meta_data2 = Coverage.ModelInstanceMetaData.objects.get(_content_type=self.page_content_type, _object_id=self.page2.id)

        self.model_meta_data = Coverage.ModelMetaData(_content_type=self.page_content_type)
        self.model_meta_data.title = u"MMD { Title"
        self.model_meta_data.keywords = u"MMD Keywords, {{ page.type }}, more keywords"
        self.model_meta_data.description = u"MMD Description for {{ page }} and {{ page }}"
        self.model_meta_data.save()

        self.context1 = get_meta_data(path=self.page1.get_absolute_url())
        self.context2 = get_meta_data(path=self.page2.get_absolute_url())

        self.view_meta_data = Coverage.ViewMetaData.objects.create(_view="userapp_my_view")
        self.view_meta_data.title = "MD {{ text }} Title"
        self.view_meta_data.keywords = "MD {{ text }} Keywords"
        self.view_meta_data.description = "MD {{ text }} Description"
        self.view_meta_data.save()

    def test_direct_data(self):
        """ Check data is used directly when it is given. """
        self.assertEqual(self.context1.keywords.value, u'MD Keywords')

    def test_populate_from_literal(self):
        # Explicit literal
        self.assertEqual(self.context1.populate_from3.value, u'efg')
        # Implicit literal is not evaluated (None)
        self.assertEqual(self.context1.populate_from4.value, None)
        self.assertEqual(self.context1.populate_from5.value, None)

    def test_populate_from_callable(self):
        # Callable given as a string
        self.assertEqual(self.context1.populate_from1.value, u'wxy')
        # Callable given as callable (method)
        self.assertEqual(self.context1.populate_from7.value, u'wxy')

    def test_populate_from_field(self):
        # Data direct from another field
        self.assertEqual(self.context1.populate_from6.value, u'MD Keywords')
        # Data direct from another field's populate_from
        self.assertEqual(self.context1.populate_from2.value, None)

    def test_fallback_order(self):
        path = self.page1.get_absolute_url()
        # Collect instances from all four meta data model for the same path
        # Each will have a title (ie field with populate_from) and a heading (ie field without populate_from)
        path_md = Coverage.PathMetaData.objects.create(_path=path, title='path title', heading="path heading")
        modelinstance_md = self.meta_data1
        model_md = self.model_meta_data
        view_md = Coverage.ViewMetaData.objects.create(_view='userapp_page_detail', title='view title', heading="view heading")
        # Correct some values
        modelinstance_md.title = "model instance title"
        modelinstance_md.heading = "model instance heading"
        modelinstance_md.save()
        model_md.title = "model title"
        model_md.heading = "model heading"
        model_md.save()
        # A convenience function for future checks
        def check_values(title, heading, heading2):
            self.assertEqual(get_meta_data(path=path).title.value, title)
            self.assertEqual(get_meta_data(path=path).heading.value, heading)
            self.assertEqual(get_meta_data(path=path).populate_from2.value, heading2)

        # Path is always found first
        check_values("path title", "path heading", "path heading")

        # populate_from is from the path model first
        path_md.title = ""
        path_md.save()
        check_values("example.com", "path heading", "path heading")

        # a field without populate_from just needs to be blank to fallback (heading)
        # a field with populate_from needs to be deleted (title) or have populate_from resolve to blank (populate_from2)
        path_md.heading = ""
        path_md.save()
        check_values("example.com", "model instance heading", "model instance heading")

        path_md.delete()
        check_values("model instance title", "model instance heading", "model instance heading")
        
        modelinstance_md.title = ""
        modelinstance_md.heading = ""
        modelinstance_md.save()
        check_values("example.com", "model heading", "model heading")

        modelinstance_md.delete()
        model_md.delete()
        check_values("view title", "view heading", "view heading")

        # Nothing matches, no meta data shown # TODO: Should populate_from be tried?
        view_md.delete()
        check_values("example.com", None, None)

    def test_model_variable_substitution(self):
        """ Simple check to see if model variable substitution is happening """
        self.assertEqual(self.context2.keywords.value, u'MMD Keywords, page-two-type, more keywords')
        self.assertEqual(self.context1.description.value, u'MMD Description for MD Page One Title and MD Page One Title')
        self.assertEqual(self.context2.description.value, u'MMD Description for Page two content. and Page two content.')

    def test_view_variable_substitution(self):
        """ Simple check to see if view variable substitution is happening """
        response = self.client.get(reverse('userapp_my_view', args=["abc123"]))
        self.assertContains(response, u'<title>MD abc123 Title</title>')
        self.assertContains(response, u'<meta name="keywords" content="MD abc123 Keywords" />')
        self.assertContains(response, u'<meta name="hs:metatag" content="MD abc123 Description" />')

    def test_not_request_context(self):
        """ Tests the view meta data on a view that is not a request context. """
        # catch logging messages
        logs = StringIO.StringIO()
        handler = logging.StreamHandler(logs)
        logging.getLogger().addHandler(handler)

        self.view_meta_data._view = "userapp_my_other_view"
        self.view_meta_data.save()
        response = self.client.get(reverse('userapp_my_other_view', args=["abc123"]))
        # Code should not throw error
        self.assertEqual(response.status_code, 200)
        # But a warning instead
        logging.getLogger('').removeHandler(handler)

        assert "{% get_metadata %} needs a RequestContext" in logs.getvalue(), "No warning logged when RequestContext not used."


class Formatting(TestCase):
    """ Formatting (unit tests)
    """
    def setUp(self):
        self.path_meta_data = Coverage.PathMetaData(
                _path        = "/",
                title       = "The <strong>Title</strong>",
                heading     = "The <em>Heading</em>",
                keywords    = 'Some, keywords", with\n other, chars\'',
                description = "A \n description with \" interesting\' chars.",
                raw1        = '<meta name="author" content="seo" /><hr /> ' 
                              'No text outside tags please.',
                raw2        = '<meta name="author" content="seo" />'
                              '<script>make_chaos();</script>')
        self.path_meta_data.save()

        self.meta_data = get_meta_data(path="/")
    
    def test_html(self):
        """ Tests html generation is performed correctly.
        """
        exp = """<title>The <strong>Title</strong></title>
<hs:tag>The <em>Heading</em></hs:tag>
<meta name="keywords" content="Some, keywords&quot;, with,  other, chars&#39;" />
<meta name="hs:metatag" content="A   description with &quot; interesting&#39; chars." />
<meta name="author" content="seo" />
<meta name="author" content="seo" />"""
        assert unicode(self.meta_data).strip() == exp.strip(), "Incorrect html:\n" + unicode(self.meta_data) + "\n\n" + unicode(exp)

    def test_description(self):
        """ Tests the tag2 is cleaned correctly. """
        exp = "A   description with &quot; interesting&#39; chars."
        self.assertEqual(self.meta_data.description.value, exp)
        exp = '<meta name="hs:metatag" content="%s" />' % exp
        self.assertEqual(unicode(self.meta_data.description), exp)

    def test_keywords(self):
        """ Tests keywords are cleaned correctly. """
        exp = "Some, keywords&quot;, with,  other, chars&#39;"
        self.assertEqual(self.meta_data.keywords.value, exp)
        exp = '<meta name="keywords" content="%s" />' % exp
        self.assertEqual(unicode(self.meta_data.keywords), exp)

    def test_inline_tags(self):
        """ Tests the title is cleaned correctly. """
        exp = 'The <strong>Title</strong>'
        self.assertEqual(self.meta_data.title.value, exp)
        exp = '<title>%s</title>' % exp
        self.assertEqual(unicode(self.meta_data.title), exp)

    def test_inline_tags2(self):
        """ Tests the title is cleaned correctly. """
        self.path_meta_data.title = "The <strong id=\"mytitle\">Title</strong>"
        self.path_meta_data.save()
        meta_data = get_meta_data(self.path_meta_data._path)
        exp = 'The <strong id=\"mytitle\">Title</strong>'
        self.assertEqual(meta_data.title.value, exp)
        exp = '<title>%s</title>' % exp
        self.assertEqual(unicode(meta_data.title), exp)

    def test_inline_tags3(self):
        """ Tests the title is cleaned correctly. """
        self.path_meta_data.title = "The < strong >Title</ strong >"
        self.path_meta_data.save()
        meta_data = get_meta_data(self.path_meta_data._path)
        exp = 'The < strong >Title</ strong >'
        self.assertEqual(meta_data.title.value, exp)
        exp = '<title>%s</title>' % exp
        self.assertEqual(unicode(meta_data.title), exp)

    def test_inline_tags4(self):
        """ Tests the title is cleaned correctly. """
        self.path_meta_data.title = "The <strong class=\"with&quot;inside\">Title</strong>"
        self.path_meta_data.save()
        meta_data = get_meta_data(self.path_meta_data._path)
        exp = 'The <strong class="with&quot;inside">Title</strong>'
        self.assertEqual(meta_data.title.value, exp)
        exp = '<title>%s</title>' % exp
        self.assertEqual(unicode(meta_data.title), exp)

    def test_inline_tags5(self):
        """ Tests the title is cleaned correctly. """
        self.path_meta_data.title = "The Title <!-- with a comment -->"
        self.path_meta_data.save()
        meta_data = get_meta_data(self.path_meta_data._path)
        exp = 'The Title <!-- with a comment -->'
        self.assertEqual(meta_data.title.value, exp)
        exp = '<title>%s</title>' % exp
        self.assertEqual(unicode(meta_data.title), exp)

    def test_forbidden_tags(self):
        """ Tests the title is cleaned correctly. """
        self.path_meta_data.title = "The <div>Title</div>"
        self.path_meta_data.save()
        meta_data = get_meta_data(self.path_meta_data._path)
        exp = 'The &lt;div&gt;Title&lt;/div&gt;'
        self.assertEqual(meta_data.title.value, exp)
        exp = '<title>%s</title>' % exp
        self.assertEqual(unicode(meta_data.title), exp)

    def test_raw1(self):
        """ Tests that raw fields in head are cleaned correctly. 
        """
        exp = '<meta name="author" content="seo" />'
        self.assertEqual(self.meta_data.raw1.value, exp)
        self.assertEqual(unicode(self.meta_data.raw1), exp)

    def test_raw2(self):
        """ Tests that raw fields in head are cleaned correctly. 
        """
        exp = '<meta name="author" content="seo" />'
        self.assertEqual(self.meta_data.raw2.value, exp)
        self.assertEqual(unicode(self.meta_data.raw2), exp)

    def test_raw3(self):
        """ Checks that raw fields aren't cleaned too enthusiastically  """
        self.path_meta_data.raw1 = '<title>Raw title 1</title>'
        self.path_meta_data.raw2 = '<title>Raw title 2</title>'
        self.path_meta_data.save()
        meta_data = get_meta_data(path="/")

        exp = '<title>Raw title 1</title>'
        self.assertEqual(meta_data.raw1.value, exp)
        self.assertEqual(unicode(meta_data.raw1), exp)
        exp = '<title>Raw title 2</title>'
        self.assertEqual(meta_data.raw2.value, exp)
        self.assertEqual(unicode(meta_data.raw2), exp)


class Definition(TestCase):
    """ Definition (System tests)
        + if "head" is True, tag is automatically included in the head
        + if "name" is included, that is the name of the given tag, otherwise, the field name is used
        + if verbose_name is used, pass on to field (through field_kwargs)
        + if the field argument given, that Django field type is used
        + if editable is set to False, no Django model field is created. The value is always from populate_from
        + if choices is given it is passed onto the field, (expanded if just a list of strings)
    """
    def test_help_text_direct(self):
        self.assert_help_text('help_text1', "Some help text 1.")

    def test_help_text_class(self):
        self.assert_help_text('help_text2', "Updated help text2.")

    def test_help_text_field(self):
        self.assert_help_text('help_text6', "Some help text 6.")
        self.assert_help_text('help_text5', "If empty, tag two will be used.")

    def test_help_text_callable(self):
        self.assert_help_text('help_text3', "Some help text 3.")
        self.assert_help_text('help_text4', "If empty, Always xyz")

    def test_help_text_literal(self):
        self.assert_help_text('populate_from3', "If empty, \"efg\" will be used.")

    def assert_help_text(self, name, text):
        self.assertEqual(Coverage.PathMetaData._meta.get_field(name).help_text, text)
        self.assertEqual(Coverage.ModelInstanceMetaData._meta.get_field(name).help_text, text)
        self.assertEqual(Coverage.ModelMetaData._meta.get_field(name).help_text, text)
        self.assertEqual(Coverage.ViewMetaData._meta.get_field(name).help_text, text)

    def test_uniqueness(self):
        # Check a path for uniqueness
        Coverage.PathMetaData.objects.create(_path="/unique/")
        try:
            Coverage.PathMetaData.objects.create(_path="/unique/")
            self.fail("Exception not raised when duplicate path created")
        except IntegrityError:
            pass

        # Check that uniqueness handles sites correctly
        current_site = Site.objects.get_current()
        WithSites.PathMetaData.objects.create(_site=current_site, _path="/unique/")
        pmd = WithSites.PathMetaData.objects.create(_site=None, _path="/unique/")
        pmd._site_id = current_site.id + 1
        pmd.save()
        try:
            WithSites.PathMetaData.objects.create(_site=current_site, _path="/unique/")
            self.fail("Exception not raised when duplicate path/site combination created")
        except IntegrityError:
            pass


class MetaOptions(TestCase):
    """ Meta options (System tests)
        + groups: these elements are grouped together in the admin and can be output together in the template
        + use_sites: add a 'site' field to each model. Non-matching sites are removed, null is allowed, meaning all sites match.
        + use_i18n:
        + use_redirect:
        + use_cache:
        + seo_models: list of models and/or apps which are available for model instance meta data
        + seo_views: list of models and/or apps which are available for model instance meta data
        - verbose_name(_plural): this is passed onto Django
        + HelpText: Help text can be applied in bulk by using a special class, like 'Meta'
    """


class Templates(TestCase):
    """ Templates (System tests)

        To write:
        - {% get_metadata ClassName on site in language for path as var %} All at once!
    """
    def setUp(self):
        self.path = "/abc/"
        Coverage.PathMetaData.objects.create(_path=self.path, title="A Title", description="A Description", raw1="Some raw text")
        self.meta_data = get_meta_data(path=self.path)
        self.context = {}

    def test_basic(self):
        self.deregister_alternatives()
        self.compilesTo("{% get_metadata %}", unicode(self.meta_data))
        self.compilesTo("{% get_metadata as var %}{{ var }}", unicode(self.meta_data))

    def test_for_path(self):
        self.deregister_alternatives()
        path = self.path
        self.path = "/another-path/"
        other_path = "/a-third-path/"
        self.compilesTo("{%% get_metadata for \"%s\" %%}" % other_path, "<title>example.com</title>")
        self.compilesTo("{%% get_metadata for \"%s\" as var %%}{{ var }}" % other_path, "<title>example.com</title>")

        self.compilesTo("{%% get_metadata for \"%s\" %%}" % path, unicode(self.meta_data))
        self.compilesTo("{%% get_metadata for \"%s\" as var %%}{{ var }}" % path, unicode(self.meta_data))

    def test_for_obj(self):
        self.deregister_alternatives()
        path = self.path
        self.path = "/another-path/"
        self.context = {'obj': {'get_absolute_url': "/a-third-path/"}}
        self.compilesTo("{% get_metadata for obj %}", "<title>example.com</title>")
        self.compilesTo("{% get_metadata for obj as var %}{{ var }}", "<title>example.com</title>")

        self.context = {'obj': {'get_absolute_url': path}}
        self.compilesTo("{% get_metadata for obj %}", unicode(self.meta_data))
        self.compilesTo("{% get_metadata for obj as var %}{{ var }}", unicode(self.meta_data))

    def test_wrong_class_name(self):
        self.compilesTo("{% get_metadata WithSites %}", "")
        self.compilesTo("{% get_metadata WithSites as var %}{{ var }}", "")

    def test_bad_class_name(self):
        try:
            self.compilesTo("{% get_metadata ThisDoesNotExist %}", "This should have raised an exception")
        except TemplateSyntaxError:
            pass
        try:
            self.compilesTo("{% get_metadata ThisDoesNotExist as var %}{{ var }}", "This should have raised an exception")
        except TemplateSyntaxError:
            pass

    def test_class_name(self):
        self.compilesTo("{% get_metadata Coverage %}", unicode(self.meta_data))
        self.compilesTo("{% get_metadata Coverage as var %}{{ var }}", unicode(self.meta_data))
        path = self.path
        self.context = {'obj': {'get_absolute_url': path}}
        self.path = "/another-path/"
        self.compilesTo("{%% get_metadata Coverage for \"%s\" %%}" % path, unicode(self.meta_data))
        self.compilesTo("{%% get_metadata Coverage for \"%s\" as var %%}{{ var }}"% path, unicode(self.meta_data))
        self.compilesTo("{% get_metadata Coverage for obj %}", unicode(self.meta_data))
        self.compilesTo("{% get_metadata Coverage for obj as var %}{{ var }}", unicode(self.meta_data))

    def test_variable_group(self):
        self.deregister_alternatives()
        self.compilesTo("{% get_metadata as var %}{{ var.advanced }}", unicode(self.meta_data.raw1))

    def test_variable_field(self):
        self.deregister_alternatives()
        self.compilesTo("{% get_metadata as var %}{{ var.raw1 }}", unicode(self.meta_data.raw1))

    def test_variable_field_value(self):
        self.deregister_alternatives()
        self.compilesTo("{% get_metadata as var %}{{ var.raw1.value }}", "Some raw text")

    def test_variable_field_name(self):
        self.deregister_alternatives()
        self.compilesTo("{% get_metadata as var %}{{ var.raw1.field.name }}", "raw1")

    def test_language(self):
        WithI18n.PathMetaData.objects.create(_path=self.path, title="A Title", _language="de")
        meta_data = seo_get_meta_data(path=self.path, name="WithSites", language="de")
        self.compilesTo('{% get_metadata WithI18n in "de" %}', unicode(meta_data))
        self.compilesTo('{% get_metadata WithI18n in "en" %}', "")

    def test_site(self):
        new_site = Site.objects.create(domain="new-example.com", name="New example")
        WithSites.PathMetaData.objects.create(_path=self.path, title="A Title", _site=new_site)
        meta_data = seo_get_meta_data(path=self.path, name="WithSites", site=new_site)
        self.compilesTo('{% get_metadata WithI18n on "new-example.com" %}', unicode(meta_data))
        self.compilesTo('{% get_metadata WithI18n in "example.com" %}', "")

    def compilesTo(self, input, expected_output):
        """ Asserts that the given template string compiles to the given output. 
        """
        input = '{% load seo %}' + input
        environ = { 'PATH_INFO': self.path, 'REQUEST_METHOD': 'GET' } 
        request = WSGIRequest(environ) 
        context= RequestContext(request)
        context.update(self.context)
        self.assertEqual(Template(input).render(context).strip(), expected_output.strip())

    def deregister_alternatives(self):
        """ Deregister any alternative meta data classes for the sake of testing. 
            This emulates the situation where there is only one meta data definition.
        """
        for key in registry.keys():
            del registry[key]
        registry['Coverage'] = Coverage

    def tearDown(self):
        # Reregister any missing classes
        if len(registry) < 5:
            registry['WithSites'] = WithSites
            registry['WithI18n'] = WithI18n
            registry['WithRedirect'] = WithRedirect
            registry['WithRedirectSites'] = WithRedirectSites


class Random(TestCase):
    """
        - Caching
            - meta data lookups are avoided by caching previous rendering for certain amount of time

    """

    def setUp(self):
        self.page = Page.objects.create(type="abc")
        self.content_type = ContentType.objects.get_for_model(Page)
        self.model_meta_data = Coverage.ModelInstanceMetaData.objects.get(_content_type=self.content_type,
                                                    _object_id=self.page.id)
        self.context = get_meta_data(path=self.model_meta_data._path)

    def test_default_fallback(self):
        """ Tests the ability to use the current Site name as a default 
            fallback. 
        """
        from django.contrib.sites.models import Site
        site = Site.objects.get_current()
        self.assertEqual(site.name, self.context.title.value)

    def test_missing_path(self):
        " Checks that a model with a missing path is gracefully ignored. "
        num_meta_data = Coverage.ModelInstanceMetaData.objects.all().count()
        try:
            no_path = NoPath.objects.create()
        except Exception, e:
            self.fail("Exception inappropriately raised: %r" % e)
        new_num_meta_data = Coverage.ModelInstanceMetaData.objects.all().count()
        self.assertEqual(num_meta_data, new_num_meta_data)


