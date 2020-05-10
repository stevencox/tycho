import os
import json
import logging
import pytest
import requests
import traceback
import uuid
import yaml
from string import Template
from tycho.context import Principal, TychoContext
from tycho.client import TychoService, TychoSystem
from unittest import mock

logger = logging.getLogger (__name__)

def __context_start_side_effect (request):    
    """
    This is a test mock. It returns a nominal response for a Tycho app launch (start) request.
    This allows us to test all registry components and their interaction with the Tycho interface
    without a running Tycho API endpoint.
    """
    return TychoSystem (**{
        "status" : "ok",
        "result" : {
            "name"       : request['name'],
            "sid"        : uuid.uuid4 (),
            "containers" :  {
                k : { 'ip_address' : 'x.y.z', 'port-1' : v }
                for k, v in request['services'].items ()
            }
        },
        "message" : "mock: testing..."
    })

def test_context ():
    """ 
    Test the TychoContext. It must be able to 
      * Load the application registry.
      * Demonstrate the ability to scope apps to a product
      * Respond to requests to launch applications which entails
        * Get metadata for each app, formulating a request to Tycho, etc.
    The test reports each failed app launch.
    It does not yet fail the build.
    When we get the initial set of apps completed, failing apps
    will fail the build.

    Example Run:  PYTHONPATH=~/dev/tycho pytest --log-cli-level=INFO test/test_registry.py

    """
    with mock.patch.object (TychoContext, '_start', side_effect=__context_start_side_effect):
        __test_context ()
def __test_context ():
    principal = Principal (username="test_user")
    seen = {}
    failed = []
    successful_total = 0
    failed_total = 0
    for product in [ "braini", "catalyst", "scidas", "blackbalsam" ]:
        tc = TychoContext (product=product)
        successful_count = 0
        failed_count = 0
        for app_id, app in tc.apps.items ():
            try:
                if app_id in seen:
                    logger.debug (f"-- skipping seen app {app_id}")
                    continue
                seen [app_id] = app_id
                system = tc.start (principal=principal, app_id=app_id)
                logger.info (f"  -- https://<UX_URL>/private/{app_id}/{principal.username}/{system.identifier}/")
                successful_count = successful_count + 1
            except Exception as e:
                logger.debug (f"App {app_id} failed. {e}")
                traceback.print_exc ()
                failed.append (app_id)
                failed_count = failed_count + 1
        logger.info (f"{product.upper()} had {successful_count} successful apps and {failed_count} failed apps.")
        successful_total = successful_total + successful_count
        failed_total = failed_total + failed_count
    logger.info (f"total of {successful_total} successful apps and {failed_total} failed apps.")
    failed_copy = failed.copy ()
    failed_copy.insert (0, "")
    fail_list = "\n==    * ".join (failed_copy)
    if len(failed) > 0:
        logger.error (f"""
=======================================
== Failed to launch the following apps:{fail_list}
=======================================""")
