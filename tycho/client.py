import requests
import json
import os
import traceback
import argparse
import yaml
from tycho.tycho_utils import TemplateUtils
from kubernetes import client as k8s_client, config as k8s_config

class TychoClient:
    """ Client to Tycho Kubernetes dynamic application deployment API. """

    def __init__(self, url):
        self.url = f"{url}/system"
    def request (self, service, request):
        response = requests.post (f"{self.url}/{service}", json=request)
        print (response.status_code)
        return response.json ()
    def start (self, request):
        return self.request ("start", request)
    def delete (self, request):
        return self.request ("delete", request)
    def down (self, name):
        try:
            response = self.delete ({ "name" : self.format_name(name) })
            print (json.dumps (response, indent=2))
        except Exception as e:
            traceback.print_exc (e)
    def format_name (self, name):
        return name.replace (os.sep, '-')
    def up (self, name, system):
        request = {
            "name" : self.format_name (name),
            "system" : system
        }
        response = self.start (request)
        error = response.get('result',{}).get('error', None)
        if error:
            print (''.join (error))
        else:
            print (json.dumps (response, indent=2))
            for process, spec in response.get('result',{}).get('containers',{}).items ():
                port = spec['port']
                print (f"http://192.168.99.111:{port}")
            
class TychoClientFactory:
    def __init__(self):
        """ Initialize connection to Kubernetes. """
        """ TODO: Authentication. """
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            k8s_config.load_incluster_config()
        else:
            k8s_config.load_kube_config()
        api_client = k8s_client.ApiClient()
        self.api = k8s_client.CoreV1Api(api_client)
    def get_client (self, name="tycho-api", namespace="default"):
        url = None
        client = None
        service = self.api.read_namespaced_service(
            name=name,
            namespace=namespace)
        try:
            ip_address = service.status.load_balancer.ingress[0].ip
            port = service.spec.ports[0].port
            url = f"http://{ip_address}:{port}"
        except Exception as e:
            traceback.print_exc (e)
        if url:
            client = TychoClient (url=url) 
        else:
            raise ValueError ("Unable to locate Tycho API endpoint.")
        return client
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tycho Client')
    parser.add_argument('-u', '--up', help="Launch service.", action='store_true')
    parser.add_argument('-d', '--down', help="Delete service.", action='store_true')
    parser.add_argument('-p', '--port', type=int, help="Port to expose.")
    parser.add_argument('-c', '--container', help="Container to run.")
    parser.add_argument('-n', '--name', help="Service name.")
    parser.add_argument('-s', '--service', help="Tycho API URL.", default="http://localhost:5000")
    parser.add_argument('--env', help="Env variable", default=None)
    parser.add_argument('--command', help="Container command", default=None)
    parser.add_argument('-f', '--file', help="A docker compose (subset) formatted system spec.")
    args = parser.parse_args ()

    client = TychoClient (url=args.service)

    name=None
    system=None
    if args.file:
        name = args.file.split('.')[0]
        with open(args.file, "r") as stream:
            system = yaml.load (stream.read ())
    else:
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
              {% endif %}"""
        system = template_utils.render_text(
            template,
            context={ "args" : args })

    client = None
    if args.service.startswith ('http://localhost'):
        """ if the default value is set, try to discover the endpoint in kube. """
        client_factory = TychoClientFactory ()
        client = client_factory.get_client ()
        if not client:
            """ that didn't work. use the default value. """
            client = TychoClient (url=args.service)
    else:
        client = TychoClient (url=args.service)

    if args.up:
        client.up (name=name, system=system)
    elif args.down:
        client.down (name=name)
