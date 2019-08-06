import argparse
import json
import logging
import os
import sys
import traceback
import yaml
from kubernetes import client as k8s_client, config as k8s_config
from tycho.compute import Compute
from tycho.exceptions import DeleteException
from tycho.exceptions import StartException
from tycho.model import System
from tycho.tycho_utils import TemplateUtils
import kubernetes.client
from kubernetes.client.rest import ApiException

logger = logging.getLogger (__name__)

class KubernetesCompute(Compute):
    """ A Kubernetes specific implementation.

        Tested with Minikube and Google Kubernetes Engine.
    """

    def __init__(self, config):
        """ Initialize connection to Kubernetes. 
        
            Connects to Kubernetes configuration using an environment appropriate method.
        """
        super(KubernetesCompute, self).__init__()
        self.config = config
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            k8s_config.load_incluster_config()
        else:
            k8s_config.load_kube_config()
        api_client = k8s_client.ApiClient()
        self.api = k8s_client.CoreV1Api(api_client)
        self.extensions_api = k8s_client.ExtensionsV1beta1Api(api_client)
        self.networking_api = k8s_client.NetworkingV1Api(api_client)

    def start (self, system, namespace="default"):
        """ Start an abstractly described distributed system on the cluster.
            Generate each required K8s artifact and wire them together. Currently 
            explicitly modeled elements include Deployment, PersistentVolume, 
            PersistentVolumeClaim, and Service components.

            :param system: An abstract system model.
            :type system: :class:`.System`
            :param namespace: Namespace to run the system in.
            :type namespace: str
        """
        try:
            utils = TemplateUtils ()

            """ Turn an abstract system model into a cluster specific representation. """
            pod_manifests = system.render ("kubernetes-pod.yaml")
            
            """ Create a persistent volume claim """
            pvc_manifests = utils.render(template="pvc.yaml",
                                        context={
                                            "system": system
                                        })
            for pvc_manifest in pvc_manifests:
                if pvc_manifest["metadata"]["name"] != "nfs":
                    response = self.api.create_namespaced_persistent_volume_claim(namespace='default', body=pvc_manifest)
                    
            """ Create Persistent Volumes. """
            pv_manifests = utils.render(template="pv.yaml",
                                       context={
                                           "system": system
                                       })
            for pv_manifest in pv_manifests:
                response = self.api.create_persistent_volume(body=pv_manifest)
        
            """ Create a deployment for the pod. """
            for pod_manifest in pod_manifests:
                deployment = self.pod_to_deployment (
                    name=system.name,
                    template=pod_manifest,
                    namespace=namespace)

            """ Create a network policy if appropriate. """
            if system.requires_network_policy ():
                logger.debug ("creating network policy")
                network_policy_manifest = system.render (
                    template="policy/tycho-default-netpolicy.yaml")
                logger.debug (f"applying network policy: {network_policy_manifest}")
                network_policy = self.networking_api.create_namespaced_network_policy (
                    body=network_policy_manifest,
                    namespace=namespace)

            """ Create service endpoints. """
            container_map = {}
            for container in system.containers:
                service = system.services.get (container.name, None)
                if service:
                    logger.debug (f"generating service for container {container.name}")
                    service_manifests = system.render (
                        template="service.yaml",
                        context={
                            "service" : service
                        })
                    logger.debug (f"creating service for container {container.name}")
                    for service_manifest in service_manifests:
                        response = self.api.create_namespaced_service(
                            body=service_manifest,
                            namespace=namespace)

                    logger.info (response)
                    """ Get IP address of allocated ingress. """
                    ip_address = self.get_service_ip_address (response)

                    logger.info (f"ingress ip: {ip_address}")
                        
                    """ Return generated node ports to caller. """
                    for port in response.spec.ports:
                        container_map[container.name] = {
                            "ip_address" : ip_address if ip_address else '--',
                            port.name : port.node_port 
                        }
                    
            result = {
                'name'       : system.name,
                'sid'        : system.identifier,
                'containers' : container_map
            }
        
        except Exception as e:
            self.delete (system.name)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            text = traceback.format_exception(
                exc_type, exc_value, exc_traceback)
            raise StartException (
                message=f"Unable to start system: {system.name}",
                details=text)

        logger.debug (f"result: {json.dumps(result,indent=2)}")
        return result

    def get_service_ip_address (self, service_metadata):
        ip_address = None
        if service_metadata.status.load_balancer.ingress and \
           len(service_metadata.status.load_balancer.ingress) > 0:
            ip_address = service_metadata.status.load_balancer.ingress[0].ip
        if not ip_address:
            ip_address = self.config['tycho']['compute']['platform']['kube']['ip']
        return ip_address
    
    def pod_to_deployment (self, name, template, namespace="default"):
        """ Create a deployment specification based on a pod template.
            
            :param name: Name of the system.
            :type name: str
            :param template: Relative path to the template to use.
            :type template: str
            :param namepsace: Namespace to run the pod in.
            :type namespace: str
        """
        deployment_spec = k8s_client.ExtensionsV1beta1DeploymentSpec(
            replicas=1,
            template=template)
        
        """ Instantiate the deployment object """
        logger.debug (f"creating deployment specification {template}")
        deployment = k8s_client.ExtensionsV1beta1Deployment(
            api_version="extensions/v1beta1",
            kind="Deployment",
            metadata=k8s_client.V1ObjectMeta(name=name),
            spec=deployment_spec)

        """ Create the deployment. """
        logger.debug (f"applying deployment {template}")
        api_response = self.extensions_api.create_namespaced_deployment(
            body=deployment,
            namespace=namespace)
        logger.debug (f"deployment created. status={api_response.status}")
        return deployment

    def delete (self, name, namespace="default"):
        """ Delete the deployment. 
                
            :param name: GUID of the system to delete.
            :type name: str
            :param namespace: Namespace the system runs in.
            :type namespace: str
        """
        try:
            """ todo: kubectl delete pv,pvc,deployment,pod,svc,networkpolicy -l executor=tycho """
            """ Delete the service. No obvious collection based api for service deletion. """
            service_list = self.api.list_namespaced_service(
                label_selector=f"tycho-guid={name}",
                namespace=namespace)
            for service in service_list.items:
                if service.metadata.labels.get ("tycho-guid", None) == name:
                    logger.info (f" --deleting service {name} in namespace {namespace}")
                    response = self.api.delete_namespaced_service(
                        name=service.metadata.name,
                        body={},
                        namespace=namespace)

            """ Treat everything with a namespace parameterized collections based delete 
            operator the same. """
            finalizers = {
                "deployment"  : self.extensions_api.delete_collection_namespaced_deployment,
                "replica_set" : self.extensions_api.delete_collection_namespaced_replica_set,
                "pod"         : self.api.delete_collection_namespaced_pod,
                "persistentvolumeclaim" : self.api.delete_collection_namespaced_persistent_volume_claim,
                "networkpolicy" : self.networking_api.delete_collection_namespaced_network_policy
            }
            for object_type, finalizer in finalizers.items ():
                logger.info (f" --deleting {object_type} elements of {name} in namespace {namespace}")
                response = finalizer (
                    label_selector=f"tycho-guid={name}",
                    namespace=namespace)
                
            logger.info (f" --deleting persistent volume {name} in namespace {namespace}")
            response = self.api.delete_collection_persistent_volume(
                label_selector=f"tycho-guid={name}")
            
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

            :param name: GUID of a system to get status for.
            :type name: str
            :param namespace: Namespace the system runs in.
            :type namespace: str
        """
        result = []
        """ Find all our generated deployments. """
        label = f"tycho-guid={name}" if name else f"executor=tycho"
        logger.debug (f"getting status using label: {label}")
        response = self.extensions_api.list_namespaced_deployment (
            namespace,
            label_selector=label)

        if response:
            for item in response.items:
                item_guid = item.metadata.labels.get ("tycho-guid", None)
                """ List all services with this guid. """
                services = self.api.list_namespaced_service(
                    label_selector=f"tycho-guid={item_guid}",
                    namespace=namespace)
                """ Inspect and report each service connected to this element separately. """
                for service in services.items:
                    ip_address = self.get_service_ip_address (service)
                    port = service.spec.ports[0].node_port
                    result.append ({
                        "name"       : service.metadata.name,
                        "sid"        : item_guid,
                        "ip_address" : ip_address,
                        "port"       : str(port)
                    })
        return result
