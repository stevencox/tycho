import requests
import json
import os
import traceback
import argparse
from kubernetes import client as k8s_client, config as k8s_config

class TychoClient:
    """ Client to Tycho Kubernetes dynamic application deployment API. """

    def __init__(self, url):
        self.url = f"{url}/system"
    def create_simple_request (self,
                               name, container, container_name, port,
                               cpu='0.3', mem='512M',
                               command=[], env=None):
        return {
            "name": name,
            "containers": [{
                "name": container_name,
                "image": container,
                "command": command,
                "env" : env,
                "limits": [{
                    "cpus": cpu,
                    "memory": mem
                }],
                "ports": [{
                    "containerPort": port
                }]
            }]
        } 
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
            response = self.delete ({ "name" : name })
            print (json.dumps (response, indent=2))
        except Exception as e:
            traceback.print_exc (e)
    def up (self, name, container, port, command=None, env=None):
        container_name = f"{name}-c" # todo: simple multi-container api.
        request = self.create_simple_request (
            name=name,
            container=container,
            container_name=container_name,
            command=command,
            env=env,
            port=port)
        response = self.start (request)
        error = response.get('result',{}).get('error', None)
        if error:
            print (''.join (error))
        else:
            print (json.dumps (response, indent=2))

        service_port = response.get('result',{}).get('containers',{}).get(container_name,{}).get('port',None)
        if service_port:
            service_url = f"http://192.168.99.111:{service_port}"
            print (f"service port: {service_port}")
            print (f"minikube service url: {service_url}")
        else:
            print ("Error, unable to get service port.")

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
    args = parser.parse_args ()

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
        client.up (name=args.name,
                   container=args.container,
                   command=args.command.split() if args.command else [],
                   env=args.env.split() if args.env else [],
                   port=args.port)
    elif args.down:
        client.down (name=args.name)
