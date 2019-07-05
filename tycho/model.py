import argparse
import datetime
import json
import os
import yaml
from jinja2 import Template

class Limits:
    """ Abstraction of resource limits on a container in a system. """
    def __init__(self,
                 cpus="0.1",
                 gpus="0",
                 memory="128M"):
        self.cpus = cpus
        self.gpus = gpus
        self.memory = memory
    def __repr__(self):
        return f"cpus:{self.cpus} gpus:{self.gpus} mem:{self.memory}"
    
class Container:
    """ Invocation of an image in a specific infastructural context. """
    def __init__(self,
                 name,
                 image,
                 command=None,
                 env=None,
                 identity=None,
                 limits=None,
                 ports=[]):
        self.name = name
        self.image = image
        self.identity = identity
        self.limits = Limits(**limits) if isinstance(limits, dict) else limits
        if isinstance(self.limits, list):
            self.limits = self.limits[0] # TODO - not sure why this is a list.
        self.ports = ports
        self.command = command
        self.env = env
    def __repr__(self):
        return f"name:{self.name} image:{self.image} id:{self.identity} limits:{self.limits}"

class System:
    """ Distributed system of interacting containerized software. """
    def __init__(self, name, containers):
        self.name = name
        assert self.name is not None, "System name is required."
        containers_exist = len(containers) > 0
        none_are_null = not any([ c for c in containers if c == None ])
        assert containers_exist and none_are_null, "System container elements may not be null."
        self.containers = list(map(lambda v : Container(**v), containers)) \
                          if isinstance(containers[0], dict) else \
                             containers
    def project (self, template):
        template_path = os.path.join (os.path.dirname (__file__), "template", template)
        self.template = None
        with open(template_path, "r") as stream:
            self.template = Template (stream.read ())
        self.template.globals['now'] = datetime.datetime.utcnow
        pod_text = self.template.render (**{
            "name" : self.name,
            "containers" : self.containers
        })        
        return yaml.load (pod_text)
    def __repr__(self):
        return f"name:{self.name} containers:{self.containers}"
    
class SystemIdentifier:
    """ Opaque unique handle to a system. """
    def __init__(self, identifier):
        self.identifier

    
