import argparse
import json
import logging
import os
import sys
import threading
import traceback
import yaml
'''
from kubernetes import client as k8s_client, config as k8s_config
from tycho.exceptions import DeleteException
from tycho.model import System
from tycho.tycho_utils import TemplateUtils
import kubernetes.client
from kubernetes.client.rest import ApiException
from compose.cli.main import TopLevelCommand, project_from_options
'''
logger = logging.getLogger (__name__)

'''
class Compute:
    """ Abstraction of a compute cluster. """
    def start (self, system, namespace="default"):
        pass
    def delete (self, name, namespace="default"):
        pass
    def status (self, name=None, namespace="default"):
        pass

class DockerComposeThread(threading.Thread):
    """ Run Docker-Compose in a thread and communicate via subprocess. """

    def __init__(self, system, port, configured, app_root):
        """ Invoke thread init and connect the system. """
        threading.Thread.__init__(self)
        self.system = system
        self.port = port
        self.container_map = {}
        self.configured = configured
        self.app_root = app_root
        
    def run (self):
        """ Execute the system. """
        logger.debug (f"creating compose app: {self.system.identifier}")
        os.makedirs (self.app_root)
        #docker_compose_file = os.path.join (self.app_root, f"docker-compose.yaml")
        docker_compose_file = os.path.join (self.app_root, f"{self.system.name}.yaml")
        env_file = os.path.join (self.app_root, ".env")

        """ For now, write literal input text. TODO, generate to incoporate policy. """
        with open (docker_compose_file, 'w') as stream:
            stream.write (self.system.source_text)
        env = f"""HOST_PORT={self.port}\nLOCAL_STORE=./\n"""
        print (f"--env----------> {env}")
        with open (env_file, 'w') as stream:
            stream.write (env)

        """ Find and return ports for each container. """
        config = yaml.load (TemplateUtils.apply_environment (
            env,
            self.system.source_text))
        logger.debug (f"Building conainer map for system {self.system.name}")
        for c_name, c_config in config.get ('services', {}).items ():
            print (f"--cname:{c_name} c_config:{c_config}")
            self.container_map[c_name] = {
                f"{c_name}-{i}" : port.split(':')[0] if ':' in port else port
                for i, port in enumerate(c_config.get('ports', []))
            }
            print (f"-- container map {self.container_map}")

        self.configured.set ()
        
        # Run docker-compose in the directory.
        logger.debug (f"Garbage collecting unused docker networks...")
        p = subprocess.Popen(
            [ "docker", "network", "prune", "--force" ],
            stdout=subprocess.PIPE,
            cwd=self.app_root)

        logger.debug (f"Running system {self.system.name} in docker-compose")
        command = f"docker-compose --project-name {self.system.name} -f {self.system.name}.yaml up --detach"
        print (command)
        p = subprocess.Popen(
            command.split (),
            stdout=subprocess.PIPE,
            cwd=self.app_root)
        
class DockerComposeCompute(Compute):
    def __init__(self):
        self.app_root_base = "apps"
    def start (self, system, namespace="default"):
        import subprocess
        """ Generate a globally unique identifier for the application. All associated 
        objects will share this identifier. """

        app_root = os.path.join (self.app_root_base, system.identifier)
        
        """ Generate a unique port for the system. Needs to be generalized to multi-container 
        while somehow preserving locally meaningful port names."""
        port = random.randint (30000, 40000)
        configured = threading.Event()
        docker_compose_thread = DockerComposeThread (system, port, configured, app_root)
        docker_compose_thread.start ()
        """ Wait for the thread to configure the app to run.
        If this takes longer than five seconds, the thread has probably errored. Continue. """
        configured.wait (5) 
        return {
            'name' : system.name,
            'sid' : system.identifier,
            'containers' : docker_compose_thread.container_map
        }

    def status (self, name, namespace="default"):
        """ Report status of running systems. """
        print (os.getcwd ())
        apps = [ guid for guid in os.listdir(self.app_root_base)
                 if os.path.isdir(os.path.join(self.app_root_base, guid)) ]
        result = []
        cur_dir = os.getcwd ()
        for app in apps:
            app_root = os.path.join (self.app_root_base, app)

            command = f"docker-compose --project-name {app} ps".split ()
            logger.debug (f"--command: {command}")
            p = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                cwd=app_root)

            p.stdout.readline ()
            for line in p.stdout:
                print (line)

            result.append ({
                "name" : "--",
                "sid"  : app,
                #"ip"   : None, #"--", #ip_address,
                "port" : "--"
            })
        return result

    def delete (self, name, namespace="default"):
        """ Delete the running process and persistent artifacts. """
        app_root = os.path.join (self.app_root_base, name)

        pattern = os.path.join (app_root, f"*{name}*.yaml")
        print (pattern)
        docker_compose_file = glob.glob (pattern)
        print (docker_compose_file)
        docker_compose_file = os.path.basename (docker_compose_file[0])
        project_name = docker_compose_file.replace (".yaml", "")
        print (f"--project name: {project_name}")
        
        command = f"docker-compose --project-name {project_name} -f {docker_compose_file} down".split ()
        """ Wait for shutdown to complete. """
        p = subprocess.check_call(
            command,
            stdout=subprocess.PIPE,
            cwd=app_root)
        
        """ Delete the app subtree. """
        shutil.rmtree (app_root)
'''

'''
class KubernetesCompute(Compute):
    """ A Kubernetes specific implementation. """

    def __init__(self):
        """ Initialize connection to Kubernetes. """
        """ TODO: Authentication. """
        super(KubernetesCompute, self).__init__()
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            k8s_config.load_incluster_config()
        else:
            k8s_config.load_kube_config()
        api_client = k8s_client.ApiClient()
        self.api = k8s_client.CoreV1Api(api_client)
        self.extensions_api = k8s_client.ExtensionsV1beta1Api(api_client)

    def start (self, system, namespace="default"):
        """ Start an abstractly described distributed system on the cluster.
        Generae each required K8s artifact and wire them together.
        """
        try:

            """ Turn an abstract system model into a cluster specific representation. """
            pod_manifest = system.project ("kubernetes-pod.yaml")
            volumes = pod_manifest['spec']['volumes']
            counter = 0
            for volume in volumes:
                """ Create a persistent volume claim """
                utils = TemplateUtils ()
                pvc_manifest = utils.render(template="pvc.yaml",
                                            context={
                                                "system": system,
                                                "volume_name": volume['name'],
                                                "claim_name": volume['persistentVolumeClaim']['claimName']
                                            })
                response = self.api.create_namespaced_persistent_volume_claim(
                    namespace='default',
                    body=pvc_manifest)
                pv_raw = system.name.split("-")
                pv_raw.pop(len(pv_raw)-1)
                pv_name = "-".join(pv_raw) + "-" + str(counter)
                counter += 1
                logger.debug (f"PV NAME {pv_name}")
                pv_manifest = utils.render(template="pv.yaml",
                                           context={
                                               "system": system,
                                               "pv_name": pv_name,
                                               "volume_name": volume['name']
                                           })
                response = self.api.create_persistent_volume(body=pv_manifest)
        
            """ Create a deployment for the pod. """
            deployment = self.pod_to_deployment (
                name=system.name,
                template=pod_manifest,
                namespace=namespace) 
        except Exception as e:
            self.delete (system.name)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            text = traceback.format_exception(
                exc_type, exc_value, exc_traceback)
            raise StartException (
                message=f"Unable to start system: {system.name}",
                details=text)
        
        """ one port mappable per container for now. """
        container_map = {}
        for container in system.containers:
            if len(container.ports) != 1:
                continue

            container_port = container.ports[0]['containerPort']
            logger.debug (f"Creating service exposing container {container.name} on port {container_port}")

            """ render the service template. """
            utils = TemplateUtils ()
            service_manifest=utils.render (template="service.yaml",
                                           context={
                                               "system" : system,
                                               "container_port" : container_port
                                           })

            response = self.api.create_namespaced_service(
                body=service_manifest,
                namespace='default')
            container_map[container.name] = {
                port.name : port.node_port for port in response.spec.ports
            }
        return {
            'name' : system.name,
            'sid' : system.identifier,
            'containers' : container_map
        }

    def pod_to_deployment (self, name, template, namespace="default"):
        
        """ Create a deployment specification. """
        deployment_spec = k8s_client.ExtensionsV1beta1DeploymentSpec(
            replicas=1,
            template=template)
        
        """ Instantiate the deployment object """
        deployment = k8s_client.ExtensionsV1beta1Deployment(
            api_version="extensions/v1beta1",
            kind="Deployment",
            metadata=k8s_client.V1ObjectMeta(name=name),
            spec=deployment_spec)

        """ Create the deployment. """
        api_response = self.extensions_api.create_namespaced_deployment(
            body=deployment,
            namespace=namespace)
        #print(f"Deployment created. status={api_response.status}")
        return deployment

    def log_status (self, response):
        if not response.status or response.status == 'Success':
            logger.debug ("--succeeded")
        elif response.status == 'Failure':
            logger.error (f"--failed: {response}")
    def delete (self, name, namespace="default"):
        """ Delete the deployment. """
        try:
            logger.info (f" --deleting deployment {name} in namespace {namespace}")
            response = self.extensions_api.delete_collection_namespaced_deployment(
                label_selector=f"tycho-guid={name}",
                namespace=namespace)
            
            logger.info (f" --deleting replica_set {name} in namespace {namespace}")
            response = self.extensions_api.delete_collection_namespaced_replica_set(
                label_selector=f"tycho-guid={name}",
                namespace=namespace)
        
            """ Delete the service. No obvious collection based api for service deletion. """
            service_list = self.api.list_namespaced_service(
            label_selector=f"tycho-guid={name}", namespace=namespace)
            for service in service_list.items:
                if service.metadata.labels.get ("tycho-guid", None) == name:
                    logger.info (f" --deleting service {name} in namespace {namespace}")
                    response = self.api.delete_namespaced_service(
                        name=service.metadata.name,
                        body={},
                        namespace=namespace)
                
            logger.info (f" --deleting pod {name} in namespace {namespace}")
            response = self.api.delete_collection_namespaced_pod(
                label_selector=f"tycho-guid={name}",
                namespace=namespace)

            logger.info (f" --deleting persistent volume {name} in namespace {namespace}")
            response = self.api.delete_collection_persistent_volume(
                label_selector=f"tycho-guid={name}")
            
            logger.info (f" --deleting persistent volume claim {name} in namespace {namespace}")
            response = self.api.delete_collection_namespaced_persistent_volume_claim(
                label_selector=f"tycho-guid={name}",
                namespace=namespace)
        
        except ApiException as e:
            traceback.print_exc (e)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            text = traceback.format_exception(
                exc_type, exc_value, exc_traceback)
            raise DeleteException (
                message=f"Failed to delete system: {name}",
                details=text)
        return {
        }
    
    def status (self, name=None, namespace="default"):
        """ Get status.
        Without a name, this will get status for all running systems.
        With a name, it will get status for the specified system.
        """
        result = []
        """ Find all our generated deployment. """
        response = self.extensions_api.list_namespaced_deployment (
            namespace,
            label_selector=f"executor=tycho")
        
        if response:
            #print(f"** response: {response}")
            for item in response.items:
                service = self.api.read_namespaced_service(
                    name=item.metadata.name,
                    namespace=namespace)
                print (service)
                ip_address = None
                """ We have a reliable way to get an IP address for load balanced services but nothing else yet. """
                if service.status.load_balancer.ingress and len(service.status.load_balancer.ingress) > 0:
                    ip_address = service.status.load_balancer.ingress[0].ip
                port = service.spec.ports[0].node_port
                #url = f"http://{ip_address}:{port}"
                print (item)
                result.append ({
                    "name" : item.metadata.name,
                    "sid"  : item.metadata.labels.get ("tycho-guid", None),
                    #"ip"   : None, #"--", #ip_address,
                    "port" : port
                })
        return result
'''
class Compute:
    """ Abstraction of a compute cluster. """
    def start (self, system, namespace="default"):
        pass
    def delete (self, name, namespace="default"):
        pass
    def status (self, name=None, namespace="default"):
        pass
