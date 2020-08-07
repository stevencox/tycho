import pytest
import sys
from tycho.model import Volumes

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


@pytest.mark.parametrize('volume_model_data', ['data1'], indirect=True)
def test_model_volume(volume_model_data):
    id_num = "333333333"
    volumes = Volumes(id_num, volume_model_data)
    data_volumes = volumes.process_volumes()
    data_volume_1 = data_volumes[0]
    assert data_volume_1["container_name"] == "nginx"
    assert data_volume_1["pvc_name"] == "nfsrods"
    assert data_volume_1["volume_name"] == "nfsrods"
    assert data_volume_1["path"] == "/home/rods"
    assert data_volume_1["subpath"] == "rods"
    data_volume_2 = data_volumes[1]
    assert data_volume_2["subpath"] == ''


