import pytest
import sys
from tycho.model import Volumes


# Sample data from conftest.py
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


