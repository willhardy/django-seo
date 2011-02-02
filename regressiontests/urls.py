from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()


# Register alternative site here to avoid double import
alternative_site = admin.AdminSite()
from rollyourown.seo.admin import auto_register_inlines
from userapp.models import Tag, Page, Product
from userapp.seo import Coverage, WithSites, WithSEOModels
alternative_site.register(Tag)
auto_register_inlines(Coverage, alternative_site)
alternative_site.register(Page)
auto_register_inlines(WithSites, alternative_site)
auto_register_inlines(WithSEOModels, alternative_site)
alternative_site.register(Product)


urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^alt-admin/', include(alternative_site.urls)),
    (r'^', include('userapp.urls')),
)
