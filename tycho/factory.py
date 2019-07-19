from tycho.kube import KubernetesCompute
from tycho.dockerc import DockerComposeCompute

config = {
    #"backplane" : "docker-compose"
    "backplane" : "kubernetes"
}
config_factory = {
    "kubernetes"     : KubernetesCompute,
    "docker-compose" : DockerComposeCompute
}

class ComputeFactory:
    @staticmethod
    def create_compute ():
        return config_factory[config['backplane']]()
