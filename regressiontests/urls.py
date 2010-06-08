from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^pages/([\w\d-]+)/', 'userapp.views.page_detail', name="userapp_page_detail"),
    url(r'^products/(\d+)/', 'userapp.views.product_detail', name="userapp_product_detail"),
    url(r'^my/view/(.+)/', 'userapp.views.my_view', name="userapp_my_view"),
    url(r'^my/other/view/(.+)/', 'userapp.views.my_other_view', name="userapp_my_other_view"),
    (r'^admin/', include(admin.site.urls)),
)
