import os
import json
import logging
import pytest
from pathlib import Path
from tycho.test.lib import client
from tycho.test.lib import system_request
# https://medium.com/@yeraydiazdiaz/what-the-mock-cheatsheet-mocking-in-python-6a71db997832

modify_data_path = os.path.dirname(os.path.abspath(__file__))
modify_data_abs_path = os.path.join(modify_data_path, "..", "json")


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


@pytest.fixture
def mock_modify_function_env_variables(mocker):
    mocker.patch.dict("os.environ", {"NAMESPACE": os.environ.get("NAMESPACE", "default")})
    yield


def get_data_for_modify_function():
    data_list = []
    files = Path(modify_data_abs_path).glob("*.json")
    for file in files:
        with open(file) as data_file:
            data_list.append(data_file.read())
    return data_list


@pytest.fixture(params=get_data_for_modify_function())
def modify_data(request):
    data = json.loads(request.param)
    yield data
