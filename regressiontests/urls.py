from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^pages/(\d+)/', 'userapp.views.page_detail', name="userapp_page_detail"),
    (r'^admin/', include(admin.site.urls)),
)
