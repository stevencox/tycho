import os
import json
import logging
import pytest
import yaml
from tycho.model import System
from tycho.core import Tycho

logger = logging.getLogger (__name__)

@pytest.fixture(scope='module')
def system():
    """ Create a Tycho request object to test with. """
    tycho = Tycho (backplane='kubernetes')
    request = {
        "name"   : "test",
        "env"    : {},
        "system" : get_sample_spec ("jupyter-ds"),
        "services" : {
            "jupyter-datascience" : {
                "port"    : "8888",
                "clients" : [ "127.0.0.1" ]
            }
        }
    }
    return tycho.parse (request)
    
def get_sample_spec (name):
    """ Load a docker-compose specification from our samples. """
    result = None
    d = os.path.dirname (__file__)
    sample_path = os.path.join (d, "..", "sample", name, "docker-compose.yaml")
    with open(sample_path, "r") as stream:
        result = yaml.load (stream)
    return result
    
def test_pod (system):
    """ Test generation and integrity of the pod (the deployment template). """
    output = system.render ("kubernetes-pod.yaml")
    print (json.dumps (output, indent=2))

    labels = output.get('metadata',{}).get('labels',{})
    pod_name = labels.get('name','')
    tycho_guid = labels.get('tycho-guid',None)
    executor = labels.get('executor','')
    
    assert executor == 'tycho'
    assert pod_name.endswith (tycho_guid)

    containers = output.get('spec',{}).get('containers',{})
    assert containers[0]['name'] == 'jupyter-datascience'
    assert containers[0]['image'] == "jupyter/datascience-notebook"
    
def test_service_template (system):
    """ Verify the generated service selects our pod correctly and is 
        otherwise correctly parameterized.
    """
    pod_spec = system.render ("kubernetes-pod.yaml")
    
    for container in system.containers:
        print (container.name)
        print (system.services)
        service = system.services.get (container.name, None)
        print (service)
        if service:
            logger.debug (f"generating service for container {container.name}")
            service_manifest = system.render (
                template="service.yaml",
                context={
                    "service" : service
                })
            print (f"{json.dumps(service_manifest,indent=2)}")
            assert service_manifest['spec']['ports'][0]['port'] == 8888
            assert service_manifest['spec']['selector']['name'] == system.name
            
            labels = pod_spec.get('metadata',{}).get('labels',{})
            assert labels['name'] == service_manifest['spec']['selector']['name']

def test_networkpolicy (system):
    """ Verify the network policy selects our pod, allows our ports, and IP blocks. """
    pod = system.render ("kubernetes-pod.yaml")
    pod_labels = pod.get('metadata',{}).get('labels',{})
    guid = pod_labels['tycho-guid']
    policy = system.render ("policy/tycho-default-netpolicy.yaml")

    found_pod_selector = True
    matched_clients = 0
    for rule in policy['spec']['ingress']:
        for f in rule.get('from', []):
            selected_guid =  f.get('podSelector',{}).get('matchLabels',{}).get('tycho-guid','')
            if selected_guid == system.identifier:
                found_pod_selector = True
            cidr = f.get('ipBlock',{}).get('cidr','')
            for name, service in system.services.items ():
                if cidr in service.clients:
                    matched_clients += 1

    assert policy['spec'].get('egress',None) == None
    assert found_pod_selector == True
    assert matched_clients == len(list(system.services.values())[0].clients)
