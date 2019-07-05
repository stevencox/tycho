import requests
import json
import os
import traceback
import argparse

class TychoClient:
    """ Client to Tycho Kubernetes dynamic application deployment API. """

    def __init__(self, url):
        self.url = f"{url}/system"
    def create_simple_request (self, name, container, container_name, port, cpu='0.3', mem='512M'):
        return {
            "name": name,
            "containers": [{
                "image": container,
                "limits": [{
                    "cpus": cpu,
                    "memory": mem
                }],
                "name": container_name,
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
    def up (self, name, container, port):
        container_name = f"{name}-c" # todo: simple multi-container api.
        request = self.create_simple_request (
            name=name,
            container=container,
            container_name=container_name,
            port=port)
        response = self.start (request)
        print (json.dumps (response, indent=2))

        service_port = response['result']['container_map'][container_name]['port']
        service_url = f"http://192.168.99.111:{service_port}"
        print (service_url)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tycho Client')
    parser.add_argument('-u', '--up', help="Launch service.", action='store_true')
    parser.add_argument('-d', '--down', help="Delete service.", action='store_true')
    parser.add_argument('-p', '--port', type=int, help="Port to expose.")
    parser.add_argument('-c', '--container', help="Container to run.")
    parser.add_argument('-n', '--name', help="Service name.")
    parser.add_argument('-s', '--service', help="Tycho API URL.", default="http://localhost:5000")
    args = parser.parse_args ()
    
    client = TychoClient (url=args.service)
    if args.up:
        client.up (name=args.name, container=args.container, port=args.port)
    elif args.down:
        client.down (name=args.name)

'''
(tycho) [scox@mac~/dev/tycho/tycho]$ PYTHONPATH=$PWD/.. python client.py --up -n jupyter-data-science-3425 -c jupyter/datascience-notebook -p 8888
200
{
  "status": "success",
  "result": {
    "container_map": {
      "jupyter-data-science-3425-c": {
        "port": 32188
      }
    }
  },
  "message": "Started system jupyter-data-science-3425"
}
http://192.168.99.111:32188
(tycho) [scox@mac~/dev/tycho/tycho]$ wget --quiet -O- http://192.168.99.111:32188 | grep -i /title
    <title>Jupyter Notebook</title>
(tycho) [scox@mac~/dev/tycho/tycho]$ PYTHONPATH=$PWD/.. python client.py --down -n jupyter-data-science-3425
200
{
  "status": "success",
  "result": null,
  "message": "Deleted system jupyter-data-science-3425"
}
(tycho) [scox@mac~/dev/tycho/tycho]$ wget --quiet -O- http://192.168.99.111:32188 | grep -i /title
(tycho) [scox@mac~/dev/tycho/tycho]$ 
'''
