import argparse
import logging
import ipaddress
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
        """ Create limits.
            
            :param cpus: Number of CPUs. May be a fraction.
            :type cpus: str
            :param gpus: Number of GPUs. May be a fraction.
            :type gpus: str
            :param memory: Amount of memory 
            :type memory: str
        """
        self.cpus = cpus
        self.gpus = gpus
        #assert (self.gpus).is_integer, "Fractional GPUs not supported"
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
        """ Construct a container.
        
            :param name: Name the running container will be given.
            :param image: Name of the image to use.
            :param command: Text of the command to run.
            :param env: Environment settings
            :type env: dict
            :param identity: UID of the user to run as.
            :type identity: int
            :param limits: Resource limits
            :type limits: dict
            :param requests: Resource requests
            :type limits: dict
            :param ports: Container ports to expose.
            :type ports: list of int
            :param volumes: List of volume mounts <host_path>:<container_path>
            :type volumes: list of str
        """
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
    def __init__(self, name, containers, services={}):
        """ Construct a new abstract model of a system given a name and set of containers.
        
            Serves as context for the generation of compute cluster specific artifacts.

            :param name: Name of the system.
            :type name: str
            :param containers: List of container specifications.
            :type containers: list of containers
        """
        self.identifier = uuid.uuid4().hex
        self.name = f"{name}-{self.identifier}"
        assert self.name is not None, "System name is required."
        containers_exist = len(containers) > 0
        none_are_null = not any([ c for c in containers if c == None ])
        assert containers_exist and none_are_null, "System container elements may not be null."
        self.containers = list(map(lambda v : Container(**v), containers)) \
                          if isinstance(containers[0], dict) else \
                             containers
        """ Construct a map of services. """
        self.services = {
            service_name : Service(**service_def)
            for service_name, service_def in services.items ()
        }
        for name, service in self.services.items ():
            service.name = f"{name}-{self.identifier}"
            
        self.source_text = None

    def requires_network_policy (self):
        return any ([ len(svc.clients) > 0 for name, svc in self.services.items () ])
    
    def render (self, template, context={}):
        """ Supply this system as a context to a template.
        
            :param template: Template 
        """
        final_context = { "system" : self }
        for n, v in context.items ():
            final_context[n] = v
        template = TemplateUtils.render (template, context=final_context)
        logger.debug (f"--generated template: {template}")
        return template

    @staticmethod
    def parse (name, system, env={}, services={}):
        """ Construct a system model based on the input request.

            Parses a docker-compose spec into a system specification.
        
            :param name: Name of the system.
            :param system: Parsed docker-compose specification.
            :param env: Dictionary of settings.
            :param services: Service specifications - networking configuration.
        """
        containers = []
        if env:
            logger.debug ("applying environment settings.")
            system_template = yaml.dump (system)
            print (json.dumps(env,indent=2))
            system_rendered = TemplateUtils.render_text (
                template_text=system_template,
                context=env)
            logger.debug (f"applied settings:\n {system_rendered}")
            system = system_rendered

        """ Model each service. """
        logger.debug (f"compose {system}")
        for cname, spec in system.get('services', {}).items ():
            """ Entrypoint may be a string or an array. Deal with either case."""            
            entrypoint = spec.get ('entrypoint', '')
            if isinstance(entrypoint, str):
                entrypoint = entrypoint.split ()
            containers.append ({
                "name"    : cname,
                "image"   : spec['image'],
                "command" : entrypoint,
                "env"     : spec.get ('environment', []),
                "limits"  : spec.get ('deploy',{}).get('resources',{}).get('limits',{}),
                "requests"  : spec.get ('deploy',{}).get('resources',{}).get('reservations',{}),
                "ports"   : [{
                    "containerPort" : p.split(':')[1] if ':' in p else p
                    for p in spec.get ("ports", [])
                }],
                "volumes"  : [ v.split(":")[1] for v in spec.get("volumes", []) ]
            })
        system_specification = {
            "name" : name,
            "containers" : containers
        }
        logger.debug (f"parsed-system: {json.dumps(system_specification, indent=2)}")
        system_specification['services'] = services
        system = System(**system_specification)
        system.source_text = yaml.dump (system)
        return system

    def __repr__(self):
        return f"name:{self.name} containers:{self.containers}"

class Service:
    """ Model network connectivity rules to the system. """
    def __init__(self, port=None, clients=[]):
        """ Construct a service object modeling network connectivity to a system. """
        self.port = port
        self.clients = list(map(lambda v: str(ipaddress.ip_network (v)), clients))
        self.name = None
        
    def __repr__(self):
        return json.dumps (
            f"service: {json.dumps({'port':self.port,'clients':self.clients}, indent=2)}")
