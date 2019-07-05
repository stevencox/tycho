import requests
import json
import os
import traceback
import argparse

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

        service_port = response.get('result',{}).get('container_map',{}).get(container_name,{}).get('port',None)
        if service_port:
            service_url = f"http://192.168.99.111:{service_port}"
            print (f"service port: {service_port}")
            print (f"minikube service url: {service_url}")
        else:
            print ("Error, unable to get service port.")
            
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
    
    client = TychoClient (url=args.service)
    if args.up:
        client.up (name=args.name,
                   container=args.container,
                   command=args.command.split() if args.command else [],
                   env=args.env.split() if args.env else [],
                   port=args.port)
    elif args.down:
        client.down (name=args.name)
