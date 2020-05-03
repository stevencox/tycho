import json
import logging
import os
import requests
import requests_cache
import traceback
import yaml
from requests_cache import CachedSession
from string import Template
from tycho.client import TychoClientFactory
from tycho.exceptions import ContextException

logger = logging.getLogger (__name__)

class Principal:
    """ Abstract representation of a system identity. """
    def __init__(self, username):
        self.username=username
        
class TychoContext:
    """
    Load, understand, and use the app registry.

    The app registry is a declarative metadata repository outlining apps available to 
    the platform. Its YAML definition structure provides 
      * Basic metadata about the registry itself including identifier, version, name, etc.
      * A list of repositories or locations apps might reference for further metadata.
      * 
    """
    
    """ https://github.com/heliumdatacommons/CommonsShare_AppStore/blob/master/CS_AppsStore/cloudtop_imagej/deployment.py """
    def __init__(self, registry_config="app-registry.yaml", product="common"):
        self.registry = self._get_registry (registry_config, product=product)
        """ Uncomment this and related lines when this code goes live,. 
        Use a timeout on the API so the unit tests are not slowed down. """
        #self.client = TychoClientFactory().get_client()
        self.product = product
        self.apps = self._grok ()
        self.http_session = CachedSession (cache_name='tycho-registry')

    def _parse_env (self, environment):
        return {
            line.split("=", maxsplit=1)[0] : line.split("=", maxsplit=1)[1]
            for line in environment.split ("\n") if '=' in line
        }
    
    def _get_registry (self, file_name, product="common"):
        """ Load the registry metadata. """
        registry = {}
        """ Load it from the Tycho conf directory for now. Perhaps more dynamic in the future. """
        registry_config = os.path.join (
            os.path.dirname (__file__),
            "conf",
            file_name)
        with open(registry_config, 'r') as stream:
            registry = yaml.safe_load (stream)
        return registry

    def _grok (self):
        """ Compile the registry, resolving text substituations, etc. """
        apps = {}
        contexts = self.registry.get ('contexts', {})
        if not self.product in contexts:
            raise ContextException (f"undefined product {self.product} not found in contexts.")
        logger.info (f"-- load-context: id:{self.product}")
        context = contexts[self.product]
        apps = context.get ('apps', {})
        """ Resolve context inheritance. """
        for base_name in context.get ('extends', []):
            if not base_name in contexts:
                raise ContextException (f"base {base_name} of context {self.product} not found in registry.")
            logger.debug (f"resolving inheritance of base {base_name} by context {self.product}")
            apps.update (contexts[base_name].get('apps'))
            new_apps = contexts[base_name].get ('apps', {})
            new_apps.update (apps)
            apps = new_apps

        """ Load the repository map to enable string interpolation. """
        repository_map = {
            key : value['url']
            for key, value in self.registry.get ('repositories', {}).items ()
        }
        """ Compile URLs to resolve repository variables. """
        for name, app in context.get('apps',{}).items ():
            for key in [ 'spec', 'icon', 'docs' ]:
                url = app[key]
                app[key] = Template(url).safe_substitute (repository_map)
        logger.debug (f"-- product {self.product} resolution => apps: {apps.keys()}")
        return apps
    
    def get_spec (self, app_id):
        """ Get the URL of the system docker-compose yaml specification. """
        spec = self.apps[app_id].get ('spec_obj', None)
        if not spec:
            url = None
            response = None
            try:
                logger.debug (f"-- resolving specification for app: {app_id}")
                url = self.apps[app_id]['spec']
                response = self.http_session.get (url)
                if response.status_code != 200:
                    raise ValueError (f"-- app {app_id}. failed to parse spec. code:{response.status_code}")
                spec = yaml.safe_load (response.text)
                self.apps[app_id]['spec_obj'] = spec
            except Exception as e:
                traceback.print_exc ()
                if response:
                    logger.error (f"-- app {app_id}. failed to parse spec. code:{response.status_code}")
                else:
                    logger.error (f"-- app {app_id}. failed to parse spec.")
                raise e
        return spec
    
    def get_settings (self, app_id):
        """ Get the URL of the .env settings / environment file. """
        env = self.apps[app_id].get ('env_obj', None)
        if not env:
            url = self.apps[app_id]['spec']
            env_url = os.path.join (os.path.dirname (url), ".env")
            logger.debug (f"-- resolving settings for app: {app_id}")
            response = self.http_session.get (env_url)
            if response.status_code == 200:
                logger.debug (f"-- got settings for {app_id}")
                env = response.text
            else:
                logger.debug (f"-- using empty settings for {app_id}")
                env = ""
            self.apps[app_id]['env_obj'] = env
        return env
    
    def start (self, principal, app_id):
        """ Get application metadata, docker-compose structure, settings, and compose API request. """
        spec = self.get_spec (app_id)
        #settings = self.client.parse_env (self.get_settings (app_id))
        settings = self._parse_env (self.get_settings (app_id))
        services = self.apps[app_id]['services']
        logger.debug (f"parsed {app_id} settings: {settings}")
        if spec is not None:
            system = self._start ({
                "name"       : app_id,
                "env"        : settings,
                "system"     : spec,
                "username"   : principal.username,
                "services"   : services
            })
            """ Validate resulting interfaces. """
            """ TODO: check returned status. """
            running = { v.name : v.port for v in system.services }
            for name, port in services.items ():
                assert name in running, f"Svc {name} expected but {services.keys()} actually running."            
            logger.info (
                f"  -- started app id:{app_id} user:{principal.username} id:{system.identifier} services:{list(running.items ())}")
        return system
    
    def _start (self, request):
        """
        Control low level application launching (start) logic. 
        Also provides an anchor point to mock the service in unit tests.
        """
        return self.client.start (request)
