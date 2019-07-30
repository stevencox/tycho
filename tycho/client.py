import requests
import json
import logging
import os
import sys
import traceback
import argparse
import yaml
from tycho.tycho_utils import TemplateUtils
from kubernetes import client as k8s_client, config as k8s_config

logger = logging.getLogger (__name__)

class TychoClient:
    """ Python client to Tycho dynamic application deployment API. """

    def __init__(self, url):
        """ Construct a client.

            :param url: URL of the Tycho API endpoint.
            :type url: string
        """
        self.url = f"{url}/system"
        
    def request (self, service, request):
        """ Send a request to the server. Generic underlayer to all requests. 

            :param service: URL path to the service to invoke.
            :param request: JSON to send to the API endpoint.
        """
        response = requests.post (f"{self.url}/{service}", json=request)
        result_text = f"HTTP status {response.status_code} received from service: {service}"
        logger.debug (result_text)
        if not response.status_code == 200:
            raise Exception (f"Error: {result_text}")
        return response.json ()
    
    def format_name (self, name):
        """ Format a service name to be a valid DNS label.
        
            :param name: Format a name.
        """
        return name.replace (os.sep, '-')

    def parse_env (self, environment):
        return {
            line.split("=", maxsplit=1)[0] : line.split("=", maxsplit=1)[1]
            for line in environment.split ("\n") if '=' in line
        }
        
    def start (self, request):
        """ Start a service. 
        
            The general format of a start request is::

                {
                   "name"   : <name of the system>,
                   "env"    : <JSON dict created from .env environment variables>,
                   "system" : <JSON of a docker-compose yaml>
                }

            :param request: A request object formatted as above.
            :type request: JSON
        """
        return self.request ("start", request)
    
    def delete (self, request):
        """ Delete a service. 
            
            Given the GUID of a running service, delete it and all its constituent parts.

            The general format of a delete request is::
        
                {
                   "name" : <GUID>
                }

            :param request: A request formatted as above.
            :type request: JSON
        """
        return self.request ("delete", request)
    
    def status (self, request):
        """ Get status of running systems.
        
            Get the status of a system by GUID or across systems.

            The format of a request is::
 
                {}

            :param request: Request formatted as above.
            :type request: JSON
        """
        return self.request ("status", request)
    
    def up (self, name, system, settings=""):
        """ Bring a service up starting with a docker-compose spec. 
        
            CLI endpoint to start a service on the Tycho compute fabric.::

                tycho up -f path/to/docker-compose.yaml

            :param name: Name of the system.
            :type name: str
            :param system: Docker-compose JSON structure.
            :type system: JSON
            :param settings: The textual contents of a .env file.
            :type settings: str
        """
        services = {}
        for container_name, container in system['services'].items ():
            ports = container['ports']
            for port in ports:
                port_num = int(port.split(':')[1] if ':' in port else port)
                services[container_name] = {
                    "port" : port_num
                    #"clients" : [ "192.16.1.179" ]
                }
                    
        request = {
            "name"   : self.format_name (name),
            "env"    : self.parse_env (settings),
            "system" : system,
            "services" : services
        }
        logger.debug (f"request: {json.dumps(request, indent=2)}")
        response = self.start (request)
        logger.debug (json.dumps(response,indent=2))
        error = response.get('result',{}).get('error', None)
        if error:
            print (''.join (error))
        else:
            format_string = '{:<30} {:<35} {:<15} {:<7}'
            print (format_string.format("SYSTEM", "GUID", "IP_ADDRESS", "PORT"))
            result = response.get('result',{})
            port='--'
            ip_address='--'
            for process, host_port in result.get('containers',{}).items ():
                ip_address = host_port['ip_address']
                port = host_port['port']
            sid = result.get ('sid',  None)
            item_name = result.get ('name', 'unknown').replace (f"-{sid}", "")
            print (format_string.format (
                TemplateUtils.trunc (item_name, max_len=28),
                TemplateUtils.trunc (sid, max_len=33),
                ip_address if ip_address else '--',
                port))
                #print (f"(minikube)=> http://192.168.99.111:{port}")
    def list (self, name, terse=False):
        """ List status of executing systems.

            CLI endpoint to list status of services.::

                tycho status
                tycho status -terse

            :param name: GUID of a service to get status for.
            :type name: str
            :param terse: Print just the GUID for running systems
            :type terse: boolean
        """
        try:
            request = { "name" : self.format_name (name) } if name else {}
            response = self.status (request)
            logger.debug (json.dumps(response,indent=2))
            status = response.get('status', None)
            #print (json.dumps(response,indent=2))
            if status  == 'success':
                items = response.get('result', [])
                if terse:
                    for item in items:
                        print (item.get ('sid', None))
                elif len(items) == 0:
                    print ('None running')
                else:
                    format_string = '{:<30} {:<35} {:<15} {:<7}'
                    print (format_string.format("SYSTEM", "GUID", "IP_ADDRESS", "PORT"))
                    for item in items:
                        ip_address = item.get('ip', '--')
                        port = item.get ('port', '--')
                        sid = item.get ('sid',  None)
                        item_name = item.get ('name', 'unknown').replace (f"-{sid}", "")
                        print (format_string.format (
                            TemplateUtils.trunc (item_name, max_len=28),
                            TemplateUtils.trunc (sid, max_len=33),
                            ip_address if ip_address else '--',
                            port if port else '--'
                        ))
            elif status == 'error':
                print (json.dumps(response, indent=2))
        except Exception as e:
            raise e #traceback.print_exc (e)
    def down (self, names):
        """ Bring down a service. 

            CLI endpoint for deleting running systems.::

                tycho down <GUID>

            :param names: GUIDs of systems to delete.
            :type name: str
        """
        try:
            for name in names:
                response = self.delete ({ "name" : self.format_name(name) })
                logger.debug (json.dumps(response,indent=2))
                if response.get('status',None) == 'success':
                    print (f"{name}")
                else:
                    print (json.dumps (response, indent=2))
        except Exception as e:
            traceback.print_exc (e)
            
class TychoClientFactory:
    """ Locate a Tycho API instance in a Kubernetes cluster.

        This is written to work wheter run in-cluster or standalone. If we're running outside of 
        the cluster we use the environment's kubernetes configuration. If we're running 
        insde kubernetes, we use the "in cluster" configuration to locate the configuration.        
    """
    def __init__(self):
        """ Initialize connection to Kubernetes.

            Load the kubernetes configuration in an enviroment appropriate way as described above.

            Then create the K8S API endpoint.
        """
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            k8s_config.load_incluster_config()
        else:
            k8s_config.load_kube_config()
        api_client = k8s_client.ApiClient()
        self.api = k8s_client.CoreV1Api(api_client)
        
    def get_client (self, name="tycho-api", namespace="default"):
        """ Locate the client endpoint using the K8s API.

            Locate the Tycho API using the K8S API. We do this by reading services in the
            given namespace with the given name. Then we look for a load balancer IP and port 
            to build a URL. This works for public cloud clusters. With some modification, it
            could work for Minikube but that is a future effort.

            :param name: Name of the Tycho API service in Kubernetes.
            :type name: str
            :param namespace: The namespace the service is deployed to.
            :type namespace: str
        """
        url = None
        client = None
        try:
            service = self.api.read_namespaced_service(
                name=name,
                namespace=namespace)
            ip_address = service.status.load_balancer.ingress[0].ip
            port = service.spec.ports[0].port
            url = f"http://{ip_address}:{port}"
        except Exception as e:
            #traceback.print_exc (e)
            logger.info (f"did not find {name} in namespace {namespace}")
        if url:
            client = TychoClient (url=url) 
        return client

if __name__ == "__main__":
    """ A CLI for Tycho. """
    status_command="@status_command"
    parser = argparse.ArgumentParser(description='Tycho Client')
    parser.add_argument('-u', '--up', help="Launch service.", action='store_true')
    parser.add_argument('-s', '--status', help="Get status of running systems.", nargs='?', const=status_command, default=None)
    parser.add_argument('-d', '--down', help="Delete a running system. Requires a system id.", nargs='*')
    parser.add_argument('-p', '--port', type=int, help="Port to expose.")
    parser.add_argument('-c', '--container', help="Container to run.")
    parser.add_argument('-n', '--name', help="Service name.")
    parser.add_argument('--service', help="Tycho API URL.", default="http://localhost:5000")
    parser.add_argument('--env', help="Env variable", default=None)
    parser.add_argument('--command', help="Container command", default=None)
    parser.add_argument('--settings', help="Environment settings", default=None)
    parser.add_argument('-f', '--file', help="A docker compose (subset) formatted system spec.")
    parser.add_argument('-t', '--trace', help="Trace (debug) logging", action='store_true', default=False)
    parser.add_argument('--terse', help="Keep status short", action='store_true', default=False)
    parser.add_argument('-v', '--volumes', help="Mounts a volume", default=None)
    args = parser.parse_args ()

    """ Honor debug and trace settings. """
    if args.trace:
        logging.basicConfig(level=logging.DEBUG)

    """ Resolve environment settings file as text. """
    settings=""
    if args.settings:
        with open(args.settings, "r") as stream:
            settings = stream.read ()

    name=args.name
    system=None
    if args.file:
        if not args.name:
            """ We've been given a docker-compose.yaml. Come up with a name for the app 
            based on the containing directory if none has been otherwise supplied. """
            if os.sep in args.file:
                args.file = os.path.abspath (args.file)
                name = args.file.split('.')[0] if '.' in args.file else args.file
                name = name.split (os.sep)[-2]
            else:
                name = os.path.basename (os.getcwd ())

        """ Apply settings. """
        env_file = os.path.join (os.path.dirname (args.file), ".env")
        if os.path.exists (env_file):
            with open (env_file, 'r') as stream:
                settings = stream.read ()
                
        with open(args.file, "r") as stream:
            system = yaml.load (stream.read ())
    else:
        """ Generate a docker-compose spec based on the CLI args. """
        name = args.name
        template_utils = TemplateUtils ()
        template = """
          version: "3"
          services:
            {{args.name}}:
              image: {{args.container}}
              {% if args.command %}
              entrypoint: {{args.command}}
              {% endif %}
              {% if args.port %}
              ports:
                - "{{args.port}}"
              {% endif %}
              {% if args.volumes %}
              volumes:
                - "{{args.volumes}}"
              {% endif %}"""

        system = template_utils.render_text(
            TemplateUtils.apply_environment (settings, template),
            context={ "args" : args })

    client = None
    """ Locate the Tycho API endpoint. Instantiate a client to use the endpoint. """
    if args.service == parser.get_default ("service"):
        """ If the endpoint is the default value, try to discover the endpoint in kube. """
        client_factory = TychoClientFactory ()
        client = client_factory.get_client ()
        if not client:
            """ That didn't work so use the default value. """
            client = TychoClient (url=args.service)
    if not client:
        logger.info (f"creating client directly {args.service}")
        client = TychoClient (url=args.service)
        
    if args.up:
        client.up (name=name, system=system, settings=settings)
    elif args.down:
        client.down (names=args.down)
    elif args.status:
        if args.status == status_command: # non arg
            client.list (name=None, terse=args.terse)
        else:
            client.list (name=args.status, terse=args.terse)
