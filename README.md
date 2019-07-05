# Tycho

[![Build Status](https://travis-ci.org/stevencox/tycho.svg?branch=master)](https://travis-ci.org/stevencox/tycho)

Tycho is an API and abstraction layer for the lifecycle management of Kubernetes applications.

While the Kubernetes API is extensive and well documented, it's also large and complex. We've chosen not to extend the full weight of that complexity to clients that need to instantiate applications in a cluster.

## Install

* Install python 3.7.x or greater.
* Create a virtual environment.
* Install the requirements.
* Start the server.

```
python3 -m venv environmentName
source environmentName/bin/activate
pip install -r requirements.txt
python api.py
```

### Usage - Development Environment Next to Minikube

This mode uses a local minikube instance with Tycho running outside of Minikube. This is the easiest way to add and test new features quickly.

Run minikube:
```
minikbue start
```
Run the minikube dashboard:
```
minikube dashboard
```
Run the Tycho API:
```
cd tycho
PYTHONPATH=$PWD/.. python api.py
```

Launch the Swagger interface `http://localhost:5000/apidocs/`.
![image](https://user-images.githubusercontent.com/306971/53313133-f1337d00-3885-11e9-8aea-83ab4a92807e.png)

Use the Tycho client to launch the Jupyter data-science notebook. It is given the name jupyter-data-science-3425 and exposes port 8888.
```
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
```

Request data from the newly created service.
```
(tycho) [scox@mac~/dev/tycho/tycho]$ wget --quiet -O- http://192.168.99.111:32188 | grep -i /title
    <title>Jupyter Notebook</title>
```
Shut down the service. This will delete all created artifacts (deployment, replica_sets, pods, services).
```
(tycho) [scox@mac~/dev/tycho/tycho]$ PYTHONPATH=$PWD/.. python client.py --down -n jupyter-data-science-3425
200
{
  "status": "success",
  "result": null,
  "message": "Deleted system jupyter-data-science-3425"
}
```
Verify the service is no longer running.
```
(tycho) [scox@mac~/dev/tycho/tycho]$ wget --quiet -O- http://192.168.99.111:32188 | grep -i /title
(tycho) [scox@mac~/dev/tycho/tycho]$ ```
```

### Usage - Within Minikube

When we deploy Tycho into Minikube it is now able to get its Kubernetes API configuration from within the cluster.

In the repo's kubernetes directory, we define deployment, pod, service, clusterrole, and clusterrolebinding models for Tycho. The following interaction shows deploying Tycho into Minikube and interacting with the API.

We first deploy all Kubernetes Tycho-api artifacts into Minkube:
```
(tycho) [scox@mac~/dev/tycho/tycho]$ kubectl create -f ../kubernetes/
deployment.extensions/tycho-api created
pod/tycho-api created
clusterrole.rbac.authorization.k8s.io/tycho-api-access created
clusterrolebinding.rbac.authorization.k8s.io/tycho-api-access created
service/tycho-api created
```
Then we use the client to launch a notebook.
```
(tycho) [scox@mac~/dev/tycho/tycho]$ PYTHONPATH=$PWD/.. python client.py --up -n jupyter-data-science-3425 -c jupyter/datascience-notebook -p 8888 -s http://192.168.99.111:$(kubectl get svc tycho-api -o json | jq .spec.ports[0].nodePort)
200
{
  "status": "success",
  "result": {
    "container_map": {
      "jupyter-data-science-3425-c": {
        "port": 31646
      }
    }
  },
  "message": "Started system jupyter-data-science-3425"
}
http://192.168.99.111:31646
```
We connect to the service to demonstrate it's running:
```
(tycho) [scox@mac~/dev/tycho/tycho]$ wget --quiet -O- http://192.168.99.111:$(kubectl get svc jupyter-data-science-3425 -o json | jq .spec.ports[0].nodePort) | grep -i /title
    <title>Jupyter Notebook</title>
```
Then we delete the service from the cluster:
```
(tycho) [scox@mac~/dev/tycho/tycho]$ PYTHONPATH=$PWD/.. python client.py --down -n jupyter-data-science-3425
200
{
  "status": "success",
  "result": null,
  "message": "Deleted system jupyter-data-science-3425"
}
```
And finally, we test the service againt to show it's no longer running:
```
(tycho) [scox@mac~/dev/tycho/tycho]$ wget --quiet -O- http://192.168.99.111:$(kubectl get svc jupyter-data-science-3425 -o json | jq .spec.ports[0].nodePort) | grep -i /title
Error from server (NotFound): services "jupyter-data-science-3425" not found
```

### Usage - Within Google Kubernetes Engine from the Google Cloud Shell

Install Python 3.7
Create a virtual environment

```
$ python3.7 -m venv venv/tycho
$ cd tycho/
$ . ../venv/tycho/bin/activate
$ pip install -r requirements.txt
```
Configure the cluster ip address and the Tycho service's node port. The tycho service's node port was exposed via the gcloud firewall in an earlier step.
```
$ external_ip=$(kubectl get nodes --output wide | grep -vi external | awk '{ print $7 }')
$ node_port=$(kubectl get svc tycho-api -o json | jq .spec.ports[0].nodePort)
$ cd tycho/
$ PYTHONPATH=$PWD/.. python client.py --up -n jupyter-data-science-3425 -c jupyter/datascience-notebook -p 8888 -s http://$external_ip:$node_port
$ gcloud compute firewall-rules update test-node-port-a --allow tcp:30991
$ wget --quiet -O- http://$external_ip:$(kubectl get svc jupyter-data-science-3425 -o json | jq .spec.ports[0].nodePort) | grep -i /title
      <title>Jupyter Notebook</title>
$ PYTHONPATH=$PWD/.. python client.py --down -n jupyter-data-science-3425 -s http://$external_ip:$node_port
```

To launch Jupyter Lab to open without prompting for a token:
```
PYTHONPATH=$PWD/.. python client.py --up -n jupyter-data-science-3425 -c jupyter/datascience-notebook -p 8888 --command "start.sh jupyter lab --LabApp.token=''"
200
{
  "status": "success",
  "result": {
    "container_map": {
      "jupyter-data-science-3425-c": {
        "port": 30756
      }
    }
  },
  "message": "Started system jupyter-data-science-3425"
}

```
