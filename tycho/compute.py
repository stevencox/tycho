import argparse
import json
import logging
import os
import yaml
import uuid
from kubernetes import client as k8s_client, config as k8s_config
from tycho.model import System
from tycho.tycho_utils import TemplateUtils
import kubernetes.client
from kubernetes.client.rest import ApiException

logger = logging.getLogger (__name__)

class Compute:
    """ Abstraction of a compute cluster. """
    def start (self, system):
        pass
class DockerComposeCompute(Compute):
    def start (self, system, namespace="default"):        
        """ Generate a globally unique identifier for the application. All associated objects will share this identifier. """
        system.name = f"{system.name}-{uuid.uuid4().hex}"
        docker_compose = f"{system.name}-docker-compose.yaml"

        with open (docker_compose, 'w') as stream:
            import yaml
            from compose.cli.main import TopLevelCommand, project_from_options
            yaml.dump (compose, stream)

        options = {
            "--no-deps": False,
            "--abort-on-container-exit": False,
            "SERVICE": "",
            "--remove-orphans": False,
            "--no-recreate": True,
            "--force-recreate": False,
            "--build": False,
            '--no-build': False,
            '--no-color': False,
            "--rmi": "none",
            "--volumes": "",
            "--follow": False,
            "--timestamps": False,
            "--always-recreate-deps": False,
            "--tail": "all",
            "-d": True,
        }
        print (__file__)
        #project = project_from_options(os.path.dirname(__file__), options)
        project = project_from_options(os.getcwd(), options)
        cmd = TopLevelCommand(project)
        def oh_my ():
            cmd.up(options)
            def fin():
                cmd.logs(options)
                cmd.down(options)
            request.addfinalizer(fin)
        from_worker ([ oh_my ])
        return {}

    '''
        with open(docker_compose, "w") as stream:
            os.system 
    '''
    def delete (self, name, namespace="default"):
        pass
    
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
        """ From the end user perspective, this probably entails creating 
        - The pod
        - The deployment
        - The service
        """

        """ Generate a globally unique identifier for the application. All associated objects will share this identifier. """
        system.name = f"{system.name}-{uuid.uuid4().hex}"
        
        """ Turn an abstract system model into a cluster specific representation. """
        pod_manifest = system.project ("kubernetes-pod.yaml")

        utils = TemplateUtils ()

        """ Create a persistent volume claim """
        pvc_manifest = utils.render(
            template="pvc.yaml",
            context={
                "system": system,
            })

        try:
            api_response_pvc = self.api.create_namespaced_persistent_volume_claim(
                namespace='default',
                body=pvc_manifest)
            print(api_response_pvc)
        except ApiException as e:
            print("Exception when calling CoreV1Api->create_namespaced_persistent_volume_claim: %s\n" % e)
        
        """ Create a persistent volume object """
        try:
            pv_raw = system.name.split("-")
            pv_raw.pop(len(pv_raw)-1)
            pv_name = "-".join(pv_raw)
            print("PV NAME", pv_name)
        except Exception as e:
            print(e)

        pv_manifest = utils.render(
            template="pv.yaml",
            context={
                "system": system,
                "pv_name": pv_name
            })

        try:
            api_response_pv = self.api.create_persistent_volume(body=pv_manifest)
            print(api_response_pv)
        except ApiException as e:
            print("Exception when calling CoreV1Api->create_persistent_volume: %s\n" % e)

        """ Create the generated pod in kube. """
        #pod_spec = self.api.create_namespaced_pod(
        #    body=pod_manifest,
        #    namespace='default')
        #print(f"Pod created. status={pod_spec}") #api_response.status}")
        
        """ Create a deployment for the pod. """
        try:
            deployment = self.pod_to_deployment (
                name=system.name,
                template=pod_manifest,
                namespace=namespace) 
        except Exception as e:
            self.delete (system.name)
        
        ''' one port mappable per container for now. '''
        container_map = {}
        for container in system.containers:
            if len(container.ports) != 1:
                continue
            container_port = container.ports[0]['containerPort']
            logger.debug (f"Creating service exposing container {container.name}")

            ''' render the service template. '''
            utils = TemplateUtils ()
            service_manifest=utils.render (
                template="service.yaml",
                context={
                    "system" : system,
                    "container_port" : container_port
                })
            
            #print (f"{json.dumps(service_manifest, indent=2)}")
            api_response = self.api.create_namespaced_service(
                body=service_manifest,
                namespace='default')
            container_map[container.name] = {
                port.name : port.node_port for port in api_response.spec.ports
            }
        return {
            'sid' : system.name,
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

    def delete (self, name, namespace="default"):
        """ Delete the deployment. """
        try:
            logger.info (f"Deleting deployment {name} in namespace {namespace}")
            api_response = self.extensions_api.delete_namespaced_deployment(
                name=name,
                body=k8s_client.V1DeleteOptions(),
                namespace=namespace)
        except Exception as e:
            print (e)

        try:
            logger.info (f"Deleting deployment {name} in namespace {namespace}")
            api_response = self.extensions_api.delete_collection_namespaced_replica_set(
                label_selector=f"name={name}",
                namespace=namespace)
        except Exception as e:
            print (e)

        """ Delete the service """
        try:
            logger.info (f"Deleting service {name} in namespace {namespace}")
            api_response = self.api.delete_namespaced_service(
                name=name,
                body=k8s_client.V1DeleteOptions(),
                namespace=namespace)
        except Exception as e:
            print (e)

        """ Delete the pod """
        try:
            logger.info (f"Deleting pod {name} in namespace {namespace}")
            '''
            api_response = self.api.delete_namespaced_pod(
                name=name,
                body=k8s_client.V1DeleteOptions(),
                namespace=namespace)
            '''
            api_response = self.api.delete_collection_namespaced_pod(
                label_selector=f"name={name}",
                namespace=namespace)
        except Exception as e:
            print (e)

        try: 
            pvc_name = "pvc-for-" + name
            api_response = self.api.delete_namespaced_persistent_volume_claim(
                name=pvc_name,
                body=k8s_client.V1DeleteOptions(), 
                namespace=namespace)
            print(f"api reponse => {api_response}")
        except ApiException as e:
            print("Exception when calling CoreV1Api->delete_namespaced_persistent_volume_claim: %s\n" % e)

        try: 
            pv_name = "pv-for-" + name
            api_response = self.api.delete_persistent_volume(
                name=pv_name,
                body=k8s_client.V1DeleteOptions())
            print(f"api response => {api_response}")
        except ApiException as e:
            print("Exception when calling CoreV1Api->delete_persistent_volume: %s\n" % e)
