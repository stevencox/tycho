# Tycho

[![Build Status](https://travis-ci.org/stevencox/tycho.svg?branch=master)](https://travis-ci.org/stevencox/tycho)

Tycho is an REST interface for the opinionated lifecycle management of Kubernetes applications.

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
Starting out, Tycho's not running on the cluster:
![image](https://user-images.githubusercontent.com/306971/60748993-b511d680-9f61-11e9-8851-ff75ca74d079.png)

First deploy the Tycho API 
```
$ kubectl create -f ../kubernetes/
deployment.extensions/tycho-api created
pod/tycho-api created
clusterrole.rbac.authorization.k8s.io/tycho-api-access created
clusterrolebinding.rbac.authorization.k8s.io/tycho-api-access created
service/tycho-api created
```

Note, here we've edited the Tycho service def to create the service as type:LoadBalancer for the purposes of a command line demo. In general, we'll access the service from within the cluster rather than exposing it externally.

That runs Tycho:
![image](https://user-images.githubusercontent.com/306971/60748922-c73f4500-9f60-11e9-8d48-fb49902dc836.png)

Initialize the Tycho API's load balancer IP and node port. 
```
$ lb_ip=$(kubectl get svc tycho-api -o json | jq .status.loadBalancer.ingress[0].ip | sed -e s,\",,g)
$ tycho_port=$(kubectl get service tycho-api --output json | jq .spec.ports[0].port)
```
Launch an application (deployment, pod, service)
```
$ PYTHONPATH=$PWD/.. python client.py --up -n jupyter-data-science-3425 -c jupyter/datascience-notebook -p 8888 -s http://$lb_ip:$tycho_port
200
{
  "status": "success",
  "result": {
    "containers": {
      "jupyter-data-science-3425-c": {
        "port": 30983
      }
    }
  },
  "message": "Started system jupyter-data-science-3425"
}
```
Refreshing the GKE cluster monitoring UI will now show the service starting:
![image](https://user-images.githubusercontent.com/306971/60749371-15574700-9f67-11e9-81cf-77ccb6724a08.png)

Then running
![image](https://user-images.githubusercontent.com/306971/60749074-e8a13080-9f62-11e9-81d2-37f6cdbfc9dc.png)

Get the job's load balancer ip and make a request to test the service.
```
$ job_lb_ip=$(kubectl get svc jupyter-data-science-3425 -o json | jq .status.loadBalancer.ingress[0].ip | sed -e s,\",,g)
$ wget --quiet -O- http://$job_lb_ip:8888 | grep -i /title
    <title>Jupyter Notebook</title>
```

And shut the service down:
```
$ PYTHONPATH=$PWD/.. python client.py --down -n jupyter-data-science-3425 -s http://$lb_ip:$tycho_port
200
{
  "status": "success",
  "result": null,
  "message": "Deleted system jupyter-data-science-3425"
}
```
This removes the deployment, pod, service, and replicasets created by the launcher.

### Usage - Environment Variables and the Command Line Client

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

For a higher degree of control, control the client from Python.
