from tycho.kube import KubernetesCompute
from tycho.dockerc import DockerComposeCompute

config = {
    "backplane" : "kubernetes"
}
config_factory = {
    "kubernetes"     : KubernetesCompute,
    "docker-compose" : DockerComposeCompute
}
supported_backplanes = config_factory.keys ()

class ComputeFactory:
    @staticmethod
    def is_valid_backplane (backplane):
        return backplane in supported_backplanes
    @staticmethod
    def set_backplane (backplane):
        config['backplane'] = backplane
    @staticmethod
    def create_compute ():
        return config_factory[config['backplane']]()
