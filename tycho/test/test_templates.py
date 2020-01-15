import os
import json
import logging
import pytest
import yaml
from tycho.model import System
from tycho.core import Tycho
from tycho.test.lib import system

logger = logging.getLogger (__name__)

def test_pod (system, request):
    print (f"{request.node.name}")
    """ Test generation and integrity of the pod (the deployment template). """
    outputs = system.render ("pod.yaml")
    for output in outputs:
        print (json.dumps (output, indent=2))

        labels = output.get('metadata',{}).get('labels',{})
        pod_name = labels.get('name','')
        tycho_guid = labels.get('tycho-guid',None)
        executor = labels.get('executor','')
    
        assert executor == 'tycho'
        assert pod_name.endswith (tycho_guid)

        containers = output.get('spec',{}).get('containers',{})
        assert containers[0]['name'] == 'jupyter-ds'
        assert containers[0]['image'] == "jupyter/datascience-notebook"
    
def test_service_template (system, request):
    print (f"{request.node.name}")
    """ Verify the generated service selects our pod correctly and is 
        otherwise correctly parameterized.
    """
    pod_specs = system.render ("pod.yaml")
    for pod_spec in pod_specs:
    
        for container in system.containers:
            print (container.name)
            print (system.services)
            service = system.services.get (container.name, None)
            print (service)
            if service:
                logger.debug (f"generating service for container {container.name}")
                service_manifests = system.render (
                    template="service.yaml",
                    context={
                        "service" : service
                    })
                for service_manifest in service_manifests:
                    print (f"{json.dumps(service_manifest,indent=2)}")
                    assert service_manifest['spec']['ports'][0]['port'] == 8888
                    assert service_manifest['spec']['selector']['name'] == system.name
            
                    labels = pod_spec.get('metadata',{}).get('labels',{})
                    assert labels['name'] == service_manifest['spec']['selector']['name']

def test_pvc_template (system, request):
    print (f"{request.node.name}")
    pvcs = system.render ("pvc.yaml")
    for index, pvc in enumerate(pvcs):
        assert pvc.get('spec',{}).get('storageClassName',None) == 'manual'
        assert pvc['spec']['resources']['requests']['storage'] == '2Gi'
        assert pvc['metadata']['labels']['name'] == system.name # Label: Same as the name of the pod.
        assert pvc['metadata']['labels']['tycho-guid'] == system.identifier # Label: Should be same as the pod.
        assert pvc['spec']['volumeName'] == system.volumes[index]['volume_name']

def test_pv_template(system, request):
    print(f"request.node.name")
    pvs = system.render("pv.yaml")
    pvcs = system.render("pvc.yaml")
    for pv_index, pv in enumerate(pvs):
        for pvc_index, pvc in enumerate(pvcs):
            if pv_index == pvc_index:
                assert pv.get("metadata",{}).get("name",None) == pvc.get("spec",{}).get("volumeName",None)
        assert pv.get("metadata",{}).get("name",None) == system.volumes[pv_index]["volume_name"]
        assert pv.get("spec",{}).get("storageClassName",None) == 'manual'
        assert pv.get("spec",{}).get("gcePersistentDisk",{}).get("pdName",None) == system.volumes[pv_index]["disk_name"]
    
def test_networkpolicy (system, request):
    """ Verify the network policy selects our pod, allows our ports, and IP blocks. """
    print (f"{request.node.name}")
    pods = system.render ("pod.yaml")
    for pod in pods:
        pod_labels = pod.get('metadata',{}).get('labels',{})
        guid = pod_labels['tycho-guid']
        policies = system.render ("policy/tycho-default-netpolicy.yaml")
        for policy in policies: 

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
 
def test_user_defined_template (system, request):
    """ Verify configured template directories are consulted to find templates, that the 
        user defined templates override the system provided templates, and that the contents
        of the user defined template are the ones generated. """
    template_path = os.path.join (os.path.dirname (__file__), "templates")
    system.config['tycho']['templates']['paths'] = [ template_path ]
    spec = system.render ("pod.yaml")
    assert list(spec)[0]['test'] == 'arbitrary_value_for_testing'
