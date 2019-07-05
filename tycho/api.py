import argparse
import json
import jsonschema
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
            print (f"ERROR: {str(error)}")
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
            "status" : "success",
            "result" : {}
        }
        try:
            self.validate (request)        
            compute = get_compute ()
            print (f"Start system request: {json.dumps(request.json, indent=2)}")
            system = System (**request.json)
            response['result'] = compute.start (System (**request.json))
            response['message'] = f"Started system {system.name}"
        except Exception as e:
            response['status'] = "error"
            response['message'] = f"Failed to start system {system.name}"
            exc_type, exc_value, exc_traceback = sys.exc_info()
            text = repr(traceback.format_exception(
                exc_type, exc_value, exc_traceback))
            response['result'] = { "error" : text }
        return response

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
            "status" : "success",
            "result" : {}
        }
        try:
            self.validate (request) 
            compute = get_compute ()
            print (f"Delete request: {json.dumps(request.json, indent=2)}")
            system_name = request.json['name']
            result = compute.delete (system_name)
            response['message'] = f"Deleted system {system_name}"
        except Exception as e:
            response['status'] = "error"
            response['message'] = f"Failed to delete system {system_name}"
            exc_type, exc_value, exc_traceback = sys.exc_info()
            text = repr(traceback.format_exception(
                exc_type, exc_value, exc_traceback))
            response['result'] = { "error" : text }
        return response

api.add_resource(StartSystemResource, '/system/start')
api.add_resource(DeleteSystemResource, '/system/delete')

if __name__ == "__main__":
   parser = argparse.ArgumentParser(description='Tycho Distributed Compute API')
   parser.add_argument('-p', '--port',  type=int, help='Port to run service on.', default=5000)
   parser.add_argument('-d', '--debug', help="Debug log level.", default=False)
   args = parser.parse_args ()
   app.run(host='0.0.0.0', port=args.port, debug=True, threaded=True)
