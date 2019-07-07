import argparse
import json
import jsonschema
import logging
import os
import requests
import sys
import traceback
import yaml
from flasgger import Swagger
from flask import Flask, jsonify, g, Response, request
from flask_restful import Api, Resource
from flask_cors import CORS
from tycho.compute import KubernetesCompute
from tycho.model import System

logger = logging.getLogger (__name__)

app = Flask(__name__)

api = Api(app)
CORS(app)

schema_file_path = os.path.join (
    os.path.dirname (__file__),
    'tycho-api-schema-0.0.1.yaml')

with open(schema_file_path, 'r') as file_obj:
    template = yaml.load(file_obj)
    
app.config['SWAGGER'] = {
    'title': 'Tycho Compute API',
    'description': 'Exploratory bioinformatic datascience via software defined distributed systems.',
    'uiversion': 3
}
swagger = Swagger(app, template=template)

def get_compute ():
    """ Connects to a compute context. """
    if not hasattr(g, 'compute'):
        g.compute = KubernetesCompute ()
    return g.compute

class TychoResource(Resource):
    """ Functionality common to Tycho services. """
    def validate (self, request):
        """ Validate a request against the schema. """
        with open(schema_file_path, 'r') as file_obj:
            specs = yaml.load(file_obj)
        to_validate = specs["components"]["schemas"]["System"]
        to_validate["components"] = specs["components"]
        to_validate["components"].pop("System", None)
        try:
            jsonschema.validate(request.json, to_validate)
        except jsonschema.exceptions.ValidationError as error:
            app.logger.error (f"ERROR: {str(error)}")
            abort(Response(str(error), 400))

class StartSystemResource(TychoResource):
    """ System initiation. """
    def post(self):
        """
        Start a system based on a specification on the compute fabric.
        ---
        tag: start
        description: Start a system on the compute fabric.
        requestBody:
            description: System start message.
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/components/schemas/System'
        responses:
            '200':
                description: Success
                content:
                    text/plain:
                        schema:
                            type: string
                            example: "Successfully validated"
            '400':
                description: Malformed message
                content:
                    text/plain:
                        schema:
                            type: string

        """
        response = {
            "status" : "success"
        }
        system = None
        try:
            app.logger.info (f"Start system request: {json.dumps(request.json, indent=2)}")
            self.validate (request)     
            system = self.get_system (request.json)
            response['result'] = get_compute().start (system)
            response['message'] = f"Started system {system.name}"
        except Exception as e:
            response['status'] = "error"
            response['message'] = f"Failed to start system {system.name if system else 'system'}"
            exc_type, exc_value, exc_traceback = sys.exc_info()
            text = traceback.format_exception(
                exc_type, exc_value, exc_traceback)
            error_text = ''.join (text)
            response['result'] = { "error" : error_text }
        return response
    def get_system (self, request):
        """ Construct a system model based on the input request. """
        result = None
        name = request['name']
        if 'system' in request:
            result = self.process_docker_compose (name, request['system'])
            app.logger.debug (f"result {result}")
            result = System(**result)
        else:
            result = System(**request)
        return result
    def process_docker_compose (self, name, compose):
        """ Parse a docker-compose spec into a system spec. """
        containers = []
        app.logger.debug (f"compose {compose}")
        for cname, spec in compose.get('services', {}).items ():
            containers.append ({
                "name"    : cname,
                "image"   : spec['image'],
                "command" : spec.get ('entrypoint', '').split(),
                "env"     : spec.get ('environment', '').split (),
                "ports"   : [
                    { "containerPort" : p.split(':')[0] if ':' in p else p
                      for p in spec.get ("ports", [])
                    }
                ]
            })
        return {
            "name" : name,
            "containers" : containers
        }
    
class DeleteSystemResource(TychoResource):
    """ System termination. """
    def post(self):
        """
        Delete a system based on a name.
        ---
        tag: start
        description: Delete a system on the compute fabric.
        requestBody:
            description: System start message.
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/components/schemas/DeleteRequest'
        responses:
            '200':
                description: Success
                content:
                    application/json:
                        schema:
                            type: string
                            example: "Successfully validated"
            '400':
                description: Malformed message
                content:
                    text/plain:
                        schema:
                            type: string

        """
        response = {
            "status" : "success"
        }
        try:
            self.validate (request) 
            logging.debug (f"Delete request: {json.dumps(request.json, indent=2)}")
            system_name = request.json['name']
            response['result'] = get_compute().delete (system_name)
            response['message'] = f"Deleted system {system_name}"
        except Exception as e:
            response['status'] = "error"
            response['message'] = f"Failed to delete system {system_name}"
            exc_type, exc_value, exc_traceback = sys.exc_info()
            text = repr(traceback.format_exception(
                exc_type, exc_value, exc_traceback))
            response['result'] = { "error" : text }
        return response

""" Register endpoints. """
api.add_resource(StartSystemResource, '/system/start')
api.add_resource(DeleteSystemResource, '/system/delete')

if __name__ == "__main__":
   parser = argparse.ArgumentParser(description='Tycho Distributed Compute API')
   parser.add_argument('-p', '--port',  type=int, help='Port to run service on.', default=5000)
   parser.add_argument('-d', '--debug', help="Debug log level.", default=False, action='store_true')
   args = parser.parse_args ()
   app.run(debug=args.debug)
   app.run(host='0.0.0.0', port=args.port, debug=True, threaded=True)
