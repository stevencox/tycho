import argparse
import logging
import json
import os
import uuid
import yaml
from tycho.tycho_utils import TemplateUtils

logger = logging.getLogger (__name__)

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
                 requests=None,
                 ports=[],
                 volumes=None):
        self.name = name
        self.image = image
        self.identity = identity
        self.limits = Limits(**limits) if isinstance(limits, dict) else limits
        self.requests = Limits(**requests) if isinstance(requests, dict) else requests
        if isinstance(self.limits, list):
            self.limits = self.limits[0] # TODO - not sure why this is a list.
        self.ports = ports
        self.command = command
        self.env = \
                   list(map(lambda v : list(map(lambda r: str(r), v.split('='))), env)) \
                   if env else []
                                                                             
        self.volumes = volumes

    def __repr__(self):
        return f"name:{self.name} image:{self.image} id:{self.identity} limits:{self.limits}"

class System:
    """ Distributed system of interacting containerized software. """
    def __init__(self, name, containers):
        """ Construct a new system given a name and set of containers. """
        self.identifier = uuid.uuid4().hex
        self.name = f"{name}-{self.identifier}"
        assert self.name is not None, "System name is required."
        containers_exist = len(containers) > 0
        none_are_null = not any([ c for c in containers if c == None ])
        assert containers_exist and none_are_null, "System container elements may not be null."
        self.containers = list(map(lambda v : Container(**v), containers)) \
                          if isinstance(containers[0], dict) else \
                             containers
        self.source_text = None
        
    def project (self, template):
        """ Create a template for this system. """
        utils = TemplateUtils ()
        return utils.render (template, context={
            "name" : self.name,
            "system_id" : self.identifier,
            "containers" : self.containers
        })
    def __repr__(self):
        return f"name:{self.name} containers:{self.containers}"
    
class SystemIdentifier:
    """ Opaque unique handle to a system. """
    def __init__(self, identifier):
        self.identifier

class SystemParser:
    """ Parse a system specification into our model. """
    def parse (self, name, structure):
        """ Construct a system model based on the input request. """
        model_args = self.parse_docker_compose (name, structure)
        logger.debug (f"result {model_args}")
        result = System(**model_args)
        result.source_text = yaml.dump (structure)
        return result
    def parse_docker_compose (self, name, compose):
        """ Parse a docker-compose spec into a system spec. """
        containers = []
        logger.debug (f"compose {compose}")
        for cname, spec in compose.get('services', {}).items ():
            """ Entrypoint may be a string or an array. Deal with either case."""
            entrypoint = spec.get ('entrypoint', '')
            if isinstance(entrypoint, str):
                entrypoint = entrypoint.split ()
            containers.append ({
                "name"    : cname,
                "image"   : spec['image'],
                "command" : entrypoint, #spec.get ('entrypoint', '').split(),
                "env"     : spec.get ('environment', []),
                "limits"  : spec.get ('deploy',{}).get('resources',{}).get('limits',{}),
                "requests"  : spec.get ('deploy',{}).get('resources',{}).get('reservations',{}),
                "ports"   : [
                    { "containerPort" : p.split(':')[1] if ':' in p else p
                      for p in spec.get ("ports", [])
                    }
                ],
                "volumes"  : [ v.split(":")[1] for v in spec.get("volumes", []) ]
            })
        #print (json.dumps(containers, indent=2))
        return {
            "name" : name,
            "containers" : containers
        }
