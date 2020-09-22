import os
import json
import logging
import pytest
import yaml
from tycho.model import System
from tycho.core import Tycho
from tycho.client import TychoClientFactory

logger = logging.getLogger (__name__)

def get_sample_spec (name):
    """ Load a docker-compose specification from our samples. """
    result = None
    d = os.path.dirname (__file__)
    sample_path = os.path.join (d, "..", "sample", name, "docker-compose.yaml")
    with open(sample_path, "r") as stream:
        result = yaml.load (stream)
    return result

def make_request ():
    """ Create a Tycho request object to test with. """
    request = {
        "name"   : "test",
        "principal": '{"username": "renci"}',
        "env"    : {},
        "system" : get_sample_spec ("jupyter-ds"),
        "services" : {
            "jupyter-datascience" : {
                "port"    : "8888",
                "clients" : [ "127.0.0.1" ]
            }
        }
    }
    return request

@pytest.fixture(scope='module')
def system_request ():
    return make_request ()
    
@pytest.fixture(scope='module')
def system(system_request):
    """ Create a Tycho request object to test with. """
    tycho = Tycho (backplane='kubernetes') 
    print (f"{json.dumps(system_request, indent=2)}")
    return tycho.parse (system_request)

@pytest.fixture(scope='module')
def client():
    return TychoClientFactory().get_client ()
