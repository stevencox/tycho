import os
import json
import logging
import pytest
import yaml
from tycho.client import TychoClient
from tycho.test.lib import client
from tycho.test.lib import system
from tycho.test.lib import system_request
from unittest import mock

logger = logging.getLogger (__name__)

def test_client_start (mocker, system_request, client, request):
    print (f"{request.node.name}")
    response = {
        "status": "success",
        "result": {
            "name": "jupyter-ds-caa94baea8a849d89e427bd78cad17eb",
            "sid": "caa94baea8a849d89e427bd78cad17eb",
            "containers": {
                "jupyter-datascience": {
                    "ip_address": "127.0.0.1",
                    "port-1": 32661
                }
            },
            "conn_string": "",
        },
        "message": "Started system jupyter-ds-caa94baea8a849d89e427bd78cad17eb"
    }
    with mock.patch.object(TychoClient, 'request', return_value=response):
        tycho_system = client.start (system_request)
        result = response['result']
        jupyter = result['containers']['jupyter-datascience']
        assert tycho_system.status == 'success'
        assert tycho_system.name == result['name']
        assert tycho_system.identifier == result['sid']
        assert tycho_system.services[0].ip_address == jupyter['ip_address']
        assert tycho_system.services[0].port == jupyter['port-1']
        assert tycho_system.message == response['message']
