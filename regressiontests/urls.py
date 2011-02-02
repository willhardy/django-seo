from django.conf.urls.defaults import *

from django.contrib import admin
from userapp import admin as userapp_admin

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^alt-admin/', include(userapp_admin.alternative_site.urls)),
    (r'^', include('userapp.urls')),
)
