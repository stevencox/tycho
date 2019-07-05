import argparse
import json
import logging
import os
import yaml
from kubernetes import client as k8s_client, config as k8s_config
from tycho.model import System

logger = logging.getLogger (__name__)

class Compute:
    """ Abstraction of a compute cluster. """
    def start (self, system):
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
        
        """ Turn an abstract system model into a cluster specific representation. """
        pod_manifest = system.project ("kubernetes-pod.yaml")
        print (f"pod --------=> {json.dumps(pod_manifest, indent=2)}")

        """ Create the generated pod in kube. """
        pod_spec = self.api.create_namespaced_pod(
            body=pod_manifest,
            namespace='default')
        print(f"Pod created. status={pod_spec}") #api_response.status}")
        
        """ Create a deployment for the pod. """
        try:
            deployment = self.pod_to_deployment (
                name=system.name,
                template=pod_spec,
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
            
            service_manifest = {
                'apiVersion': 'v1',
                'kind': 'Service',
                'metadata': {
                    'labels': {'name': system.name},
                    'name': system.name,
                    'resourceversion': 'v1'},
                'spec': {
                    'type' : 'NodePort',
                    'ports': [{'name': 'port',
                               'port': container_port,
                               'protocol': 'TCP',
                               'targetPort': container_port }],
                    'selector': {'name': system.name}}}

            print (f"{json.dumps(service_manifest, indent=2)}")
            api_response = self.api.create_namespaced_service(
                body=service_manifest,
                namespace='default')
            container_map[container.name] = {
                port.name : port.node_port for port in api_response.spec.ports
            }
            print(f"Service created. status={api_response.status}")
        return {
            #'pod_spec' : pod_spec,
            'container_map' : container_map
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
        print(f"Deployment created. status={api_response.status}")
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
#                body=k8s_client.V1DeleteOptions(),
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

