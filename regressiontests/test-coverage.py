#!/usr/bin/env python

"""
Run Django Tests with full test coverage

This starts coverage early enough to get all of the model loading &
other startup code. It also allows you to change the output location
from $PROJECT_ROOT/coverage by setting the $TEST_COVERAGE_OUTPUT_DIR
environmental variable.

This is a customised version of the django coverage tool by acdha,
downloaded from http://gist.github.com/288810

Modified by Will Hardy (will@hardysoftware.de) June 2010.
"""

import logging
import os
import sys
from coverage import coverage

def main():
    PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
    output_dir = os.environ.get("TEST_COVERAGE_OUTPUT_DIR", os.path.join(PROJECT_ROOT, "coverage"))
    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        import settings as sett
        os.environ["DJANGO_SETTINGS_MODULE"] = sett.__name__

    print >>sys.stderr, "Test coverage output will be stored in %s" % output_dir

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s', filename=os.path.join(output_dir, "tests.log"))

    from django.conf import settings

    # Start code coverage before anything else if necessary
    use_coverage = hasattr(settings, 'COVERAGE_MODULES') and len(settings.COVERAGE_MODULES)
    if use_coverage:
        if len(sys.argv) > 1 and sys.argv[1] == "--branch":
            sys.argv.pop(1)
            cov = coverage(branch=True) # Enable super experimental branch support
        else:
            cov = coverage()
        cov.use_cache(0) # Do not cache any of the coverage.py stuff
        cov.exclude('^\s*$') # Exclude empty lines
        cov.exclude('^\s*#.*$') # Exclude comment blocks
        cov.exclude('^\s*(import|from)\s') # Exclude import statements
        cov.start()

    from django.conf import settings
    from django.db.models import get_app, get_apps


    # NOTE: Normally we'd use ``django.core.management.commands.test`` here but
    # we want to have South's intelligence for applying database migrations or
    # syncing everything directly (based on ``settings.SOUTH_TESTS_MIGRATE``).
    # South's test Command is a subclass of the standard Django test Command so
    # it's otherwise identical:
    try:
        from south.management.commands import test
    except ImportError:
        from django.core.management.commands import test

    # Suppress debugging displays, etc. to test as real users will see it:
    settings.DEBUG = False
    settings.TEMPLATE_DEBUG = False
    # This avoids things being cached when we attempt to regenerate them.
    settings.CACHE_BACKEND = 'dummy:///'

    # According to http://docs.djangoproject.com/en/1.0/topics/cache/#order-of-middleware-classes
    # this should not be ahead of UpdateCacheMiddleware but to avoid this unresolved Django bug
    # http://code.djangoproject.com/ticket/5176 we have to place SessionMiddleware first to avoid
    # failures:
    mc = list(settings.MIDDLEWARE_CLASSES)
    try:
        mc.remove('django.middleware.cache.FetchFromCacheMiddleware')
        mc.remove('django.middleware.cache.UpdateCacheMiddleware')
    except ValueError:
        pass

    settings.MIDDLEWARE_CLASSES = tuple(mc)

    # If the user provided modules on the command-line we'll only test the
    # listed modules. Otherwise we'll build a list of installed applications
    # which we wrote and pretend the user entered that on the command-line
    # instead.

    test_labels = [ i for i in sys.argv[1:] if not i[0] == "-"]
    if not test_labels:
        test_labels = []

        site_name = settings.SETTINGS_MODULE.split(".")[0]

        for app in get_apps():
            pkg = app.__package__ or app.__name__.replace(".models", "")
            if pkg in settings.COVERAGE_MODULES:
                test_labels.append(pkg)
            else:
                print >>sys.stderr, "Skipping tests for %s" % pkg

        test_labels.sort()

        print >>sys.stderr, "Automatically generated test labels for %s: %s" % (site_name, ", ".join(test_labels))

        sys.argv.extend(test_labels)

    settings.DEBUG = False
    settings.TEMPLATE_DEBUG = False

    command = test.Command()

    rc = 0
    sys.argv.insert(1, "test")
    try:
        command.run_from_argv(sys.argv)
    except SystemExit, e:
        rc = e.code

    # Stop code coverage after tests have completed
    if use_coverage:
        cov.stop()

    coverage_modules = filter(None, [
        sys.modules[k] for k in sys.modules if any(
            l for l in [ l.split(".")[0] for l in test_labels]
                # Avoid issues with an empty models.py causing __package__ == None
                if k.startswith(get_app(l).__package__ or get_app(l).__name__.replace(".models", ""))
        )
    ])

    if use_coverage:
        # Print code metrics header
        print ''
        print '-------------------------------------------------------------------------'
        print ' Unit Test Code Coverage Results'
        print '-------------------------------------------------------------------------'
    
        # Report code coverage metrics
        cov.report(coverage_modules)

        cov.html_report(coverage_modules, directory=output_dir)
        cov.xml_report(coverage_modules, outfile=os.path.join(output_dir, "coverage.xml"))

        # Print code metrics footer
        print '-------------------------------------------------------------------------'

        if rc != 0:
            print >>sys.stderr, "Coverage report is not be accurate due to non-zero exit status: %d" % rc

        sys.exit(rc)


if __name__ == "__main__":
    main()
