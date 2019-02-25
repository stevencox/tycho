import argparse
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
                 identity,
                 limits):
        self.name = name
        self.image = image
        self.identity = identity
        self.limits = Limits(**limits) if isinstance(limits, dict) else limits
        if isinstance(self.limits, list):
            self.limits = self.limits[0] # TODO - not sure why this is a list.
    def __repr__(self):
        return f"name:{self.name} image:{self.image} id:{self.identity} limits:{self.limits}"

class System:
    """ Distributed system of interacting containerized software. """
    def __init__(self, name, containers):
        self.name = name
        self.containers = list(map(lambda v : Container(**v), containers)) \
                          if isinstance(containers, dict) else \
                             containers
        assert self.name is not None, "System name is required."
        containers_exist = len(self.containers) > 0
        none_are_null = not any([ c for c in self.containers if c == None ])
        assert containers_exist and none_are_null, "System container elements may not be null."
    def project (self, template):
        template_path = os.path.join (os.path.dirname (__file__), "template", template)
        self.template = None
        with open(template_path, "r") as stream:
            self.template = Template (stream.read ())
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
        
def main ():
    """ Process arguments. """
    arg_parser = argparse.ArgumentParser(
        description='StageCluster',
        formatter_class=lambda prog: argparse.ArgumentDefaultsHelpFormatter(prog,
                                                                            max_help_position=180))
    arg_parser.add_argument('-v', '--verbose', help="Verbose mode.", action="store_true")
    arg_parser.add_argument('-b', '--xyz', help="...", default="...")
    System (**{
        "name" : "test",
        "containers" : [
            {
                "image" : "nginx",
                "name"  : "nginx-container",
                "limits" : {
                    "cpus" : "0.1",
                    "memory" : "512M"
                }
            }
        ]
    })
    
if __name__ == '__main__':
    main ()
    
