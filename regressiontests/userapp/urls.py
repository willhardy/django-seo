#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('userapp.views', 
    url(r'^pages/([\w\d-]+)/', 'page_detail', name="userapp_page_detail"),
    url(r'^products/(\d+)/', 'product_detail', name="userapp_product_detail"),
    url(r'^my/view/(.+)/', 'my_view', name="userapp_my_view"),
    url(r'^my/other/view/(.+)/', 'my_other_view', name="userapp_my_other_view"),
    )
