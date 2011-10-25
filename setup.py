#!/usr/bin/env python2.5
# -*- coding: UTF-8 -*-

try:
    import ez_setup
    ez_setup.use_setuptools()
except ImportError:
    pass

from setuptools import setup, find_packages

setup(
    name = "DjangoSEO",
    version = '1.0',
    packages = find_packages(exclude=["docs*", "regressiontests*"]),
    namespace_packages = ['rollyourown'],
    requires = ['django (>=1.1)'],
    author = "Will Hardy",
    author_email = "djangoseo@willhardy.com.au",
    description = "A framework for managing SEO metadata in Django.",
    long_description = open('README').read(),
    license = "LICENSE",
    keywords = "seo, django, framework",
    url = "https://github.com/willhardy/django-seo",
    include_package_data = True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "License :: OSI Approved :: Apache Software License",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Software Development"
    ],
)

