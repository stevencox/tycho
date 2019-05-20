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
        k8s_config.load_kube_config()
        api_client = k8s_client.ApiClient()
        self.api = k8s_client.CoreV1Api(api_client)
        self.extensions_api = k8s_client.ExtensionsV1beta1Api(api_client)

    def start (self, system):
        """ From the end user perspective, this probably entails creating 
        - The pod
        - The deployment
        - The service
        """
        namespace="default" # for now
        
        """ Turn an abstract system model into a cluster specific representation. """
        pod_manifest = system.project ("kubernetes-pod.yaml")
        print (f"pod --------=> {json.dumps(pod_manifest, indent=2)}")

        """ Create the generated pod in kube. """
        pod_spec = self.api.create_namespaced_pod(
            body=pod_manifest,
            namespace='default')
        print(f"Pod created. status={pod_spec}") #api_response.status}")
        
        """ Create a deployment for the pod. """
        deployment = self.pod_to_deployment (
            name=system.name,
            template=pod_spec) 
        
        service_manifest = {'apiVersion': 'v1',
                            'kind': 'Service',
                            'metadata': {
                                'labels': {'name': system.name},
                                'name': system.name,
                                'resourceversion': 'v1'},
                            'spec': {
                                'type' : 'NodePort',
                                'ports': [{'name': 'port',
                                           'port': 80, # more params.
                                           'protocol': 'TCP',
                                           'targetPort': 80}],
                                'selector': {'name': system.name}}}
        print (f"{json.dumps(service_manifest, indent=2)}")
        api_response = self.api.create_namespaced_service(
            body=service_manifest,
            namespace='default')
        print(f"Service created. status={api_response.status}")
        return pod_spec

    def pod_to_deployment (self, name, template):
        
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
            namespace="default")
        print(f"Deployment created. status={api_response.status}")
        return deployment
