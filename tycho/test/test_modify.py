import os
import json

from pytest import mark
from pytest import fixture

from tycho.client import TychoClient


@mark.skip(reason="Need connection to a running Kubernetes cluster and a valid guid.")
@mark.kubernetes
class TestModify:

    def test_modify_functional(self, modify_data, mock_modify_function_env_variables):
        client = TychoClient()
        response = client.patch(modify_data)
        if response["status"] == "success":
            assert True
        else:
            assert False
