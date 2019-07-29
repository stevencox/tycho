import ipaddress
import json
import logging
import os
import yaml
import traceback
import re
from tycho.tycho_utils import Resource

logger = logging.getLogger (__name__)

class Config(dict):
    def __init__(self, config, prefix=''):
        
        if isinstance(config, str):
            config_path = Resource.get_resource_path (config)
            logger.debug (f"loading config: {config_path}")
            with open(config_path, 'r') as f:
                self.conf = yaml.safe_load (f)
        elif isinstance(config, dict):
            self.conf = config
        else:
            raise ValueError
        self.prefix = prefix
        logger.debug (f"loaded config: {json.dumps(self.conf,indent=2)}")
        if 'TYCHO_ON_MINIKUBE' in os.environ:
            ip = os.popen('minikube ip').read().strip ()
            if len(ip) > 0:
                try:
                    ipaddress.ip_address (ip)
                    logger.info (f"Configuring minikube ip: {ip}")
                    self.conf['tycho']['compute']['platform']['kube']['ip'] = ip
                except ValueError as e:
                    logger.error ("Unable to get minikube ip address")
                    traceback.print_exc (e)
                    

    '''
    def __setitem__(self, key, val):
        raise TypeError("Setting configuration is not allowed.")

    def __str__(self):
        return "Config with keys: "+', '.join(list(self.conf.keys()))
    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default
    def __getitem__(self, key):
        """
        Use this accessor instead of getting conf directly in order to permit overloading with environment variables.
        Imagine you have a config file of the form

          person:
            address:
              street: Main

        This will be overridden by an environment variable by the name of PERSON_ADDRESS_STREET,
        e.g. export PERSON_ADDRESS_STREET=Gregson
        """
        result = None
        key_var = re.sub('[\W]', '', key)
        name = self.prefix+'_'+key_var if self.prefix else key_var
        logger.debug (f"config looking for {name}")
        try:
            env_name = name.upper()
            logger.debug (f"  --found key {env_name} in environment")
            result = os.environ[env_name]
        except KeyError:
            value = self.conf[key]
            #print(f'GOT {value}')
            if isinstance(value, dict):
                result = Config(value, prefix=name)
            else:
                result = value
        logger.debug (f"returning result: {result}")
        return result
    '''
    def __setitem__(self, key, val):
        self.conf.__setitem__(key, val)
    def __str__(self):
        return self.conf.__str__()
    def __getitem__(self, key):
        return self.conf.__getitem__(key)
    def get (self, key, default=None):
        return self.conf.get(key, default)
