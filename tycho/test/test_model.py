import os
import json
import yaml
from tycho.model import System
from tycho.config import Config

def test_system_model (request):
    """ Test that the abstract model parses structures as we expect and puts the pieces
    where they belong. """
    print (f"{request.node.name}")
    system = System (**{
        "config"     : Config (),
        "name"       : "test",
        "principal"   : {"username": "renci"},
        "serviceAccount": "default",
        "conn_string": "",
        "containers" : [
            {
                "name"  : "nginx-container",
                "image" : "nginx:1.9.1",
                "limits" : [{
                    "cpus" : "0.5",
                    "memory" : "512M"
                }],
                "volumes": [],
            }
        ]
    }) 
    print(system.containers[0].limits)
    assert system.name.startswith ('test-')
    assert system.containers[0].name == 'nginx-container'
    assert system.containers[0].image == 'nginx:1.9.1'
    assert system.containers[0].limits['cpus'] == "0.5"
    assert system.containers[0].limits['memory'] == "512M"

def test_system_parser (request):
    """ Test parsing of a docker-compose into the standard model. """
    print (f"{request.node.name}")
    base_dir = os.path.dirname (os.path.dirname (__file__))
    spec_path = os.path.join (base_dir, "sample", "jupyter-ds", "docker-compose.yaml")
    with open (spec_path, "r") as stream:
        structure = yaml.load (stream)
        system =  System.parse (
            config = Config (),
            name   = "jupyter-ds",
            principal = '{"username": "renci"}',
            system = structure,
            serviceAccount = "default")

        print (f"{system}")
        assert system.name.startswith ('jupyter-ds')
        assert system.containers[0].name == 'jupyter-ds'
        assert system.containers[0].image == 'jupyter/datascience-notebook'
        assert system.containers[0].limits.cpus == '0.01'
        assert system.containers[0].limits.memory == '50M'
        assert system.containers[0].requests.cpus == '0.01'
        assert system.containers[0].requests.memory == '20M'
        assert system.containers[0].ports[0]['containerPort'] == '8888'
        assert system.containers[0].volumes[0] == 'pvc://cloud-top/projects:/work/data'




        
