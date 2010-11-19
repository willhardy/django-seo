#!/usr/bin/env python
# -*- coding: UTF-8 -*-

try:
    import ez_setup
    ez_setup.use_setuptools()
except ImportError:
    pass

from setuptools import setup, find_packages

setup(
    name = "Django SEO",
    version = '1.0 beta 1',
    packages = find_packages(exclude=["docs*", "regressiontests*"]),
    install_requires = ['django>=1.0'],
    author = "Will Hardy",
    author_email = "djangoseo@hardysoftware.com.au",
    description = "A framework for managing SEO metadata in Django.",
    long_description = open('README.rst').read(),
    license = "LICENSE.txt",
    keywords = "seo, django, framework",
    #url = "http://seo.hardysoftware.com.au/",
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

