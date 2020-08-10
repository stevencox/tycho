import logging
import pytest
from tycho.test.lib import client
from tycho.test.lib import system_request
# https://medium.com/@yeraydiazdiaz/what-the-mock-cheatsheet-mocking-in-python-6a71db997832

@pytest.fixture(params=["data1", "data2"])
def volume_model_data(request):
    if request.param is "data1":
        data = [{
            "name": "nginx",
            "image": "sample/image:v1",
            "command": "some entrypoint",
            "env": [],
            "limits": [],
            "requests": {},
            "ports": [],
            "expose": [],
            "depends_on": [],
            "volumes": ["pvc://nfsrods/rods:/home/rods", "pvc://cloud-top:/home/shared"]
        }]
        return data
    if request.param is "data2":
        data = [
            {'container_name': 'nginx',
             'pvc_name': 'nfsrods',
             'volume_name': 'nfsrods',
             'path': '/home/rods',
             'subpath': 'rods'
             },
            {'container_name': 'nginx',
             'pvc_name': 'cloud-top',
             'volume_name': 'cloud-top',
             'path': '/home/shared',
             'subpath': ''
             }
        ]
        return data
