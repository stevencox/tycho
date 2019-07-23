import argparse
import ipaddress
import json
import jsonschema
import logging
import netifaces
import os
import requests
import sys
import traceback
import yaml
from flasgger import Swagger
from flask import Flask, jsonify, g, Response, request
from flask_restful import Api, Resource
from flask_cors import CORS
from tycho.factory import ComputeFactory
from tycho.factory import supported_backplanes
from tycho.model import SystemParser
from tycho.model import System

logger = logging.getLogger (__name__)

app = Flask(__name__)

api = Api(app)
CORS(app)
debug=False

schema_file_path = os.path.join (
    os.path.dirname (__file__),
    'api-schema.yaml')

with open(schema_file_path, 'r') as file_obj:
    template = yaml.load(file_obj)
    
app.config['SWAGGER'] = {
    'title': 'Tycho Compute API',
    'description': 'An API, compiler, and executor for cloud native distributed systems.',
    'uiversion': 3
}
swagger = Swagger(app, template=template)

def get_compute ():
    """ Connects to a compute context. """
    if not hasattr(g, 'compute'):
        g.compute = ComputeFactory.create_compute ()
    return g.compute

class TychoResource(Resource):
    def __init__(self):
        self.specs = {}

    def get_client_ip (self, request):
        ip_addr = request.remote_addr
        if debug:
            interface = netifaces.ifaddresses ('en0')
            ip_addr = interface[2][0]['addr']
            #cidr = ipaddress.ip_network(ip_addr)
        app.logger.debug (f"(debug mode ip addr:)--> {ip_addr}")
        return ip_addr
    
    """ Functionality common to Tycho services. """
    def validate (self, request, component):
        """ Validate a request against the schema. """
        if not self.specs:
            with open(schema_file_path, 'r') as file_obj:
                self.specs = yaml.load(file_obj)
        to_validate = self.specs["components"]["schemas"][component]
        try:
            app.logger.debug (f"--:Validating obj {json.dumps(request.json, indent=2)}")
            app.logger.debug (f"  schema: {json.dumps(to_validate, indent=2)}")            
            jsonschema.validate(request.json, to_validate)
        except jsonschema.exceptions.ValidationError as error:
            app.logger.error (f"ERROR: {str(error)}")
            traceback.print_exc (error)
            abort(Response(str(error), 400))

class StartSystemResource(TychoResource):
    """ Parse, model, emit orchestrator artifacts and execute a system. """
    
    def __init__(self):        
        super().__init__()
        self.system_parser = SystemParser ()
        
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
        ip_addr = self.get_client_ip (request)
        response = {}
        try:
            app.logger.info (f"start-system: {json.dumps(request.json, indent=2)}")
            self.validate (request, component="System")
            system = self.system_parser.parse (
                name=request.json['name'],
                structure=request.json['system'],
                settings=request.json['env'],
                firewall={
                    'ingress_ports' : [ '80' ],
                    'egress_ports' : [],
                    'ingress_cidrs' : [ ipaddress.ip_network(ip_addr) ],
                    'egress_cidrs' : []
                })
            response = {
                'status'  : 'success',
                'result'  : get_compute().start (system),
                'message' :  f"Started system {system.name}"
            }
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            text = traceback.format_exception(exc_type, exc_value, exc_traceback)
            error_text = ''.join (text)
            response = {
                'status' : "error",
                'message' : f"Failed to start system",
                'result' : { "error" : error_text }
            }
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
        response = {}
        try:
            logging.debug (f"delete-request: {json.dumps(request.json, indent=2)}")
            self.validate (request, component="DeleteRequest")
            system_name = request.json['name']
            response = {
                'status'  : 'success',
                'result'  : get_compute().delete (system_name),
                'message' : f"Deleted system {system_name}"
            }
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            text = repr(traceback.format_exception(exc_type, exc_value, exc_traceback))
            response = {
                'status'  : "error",
                'message' : f"Failed to delete system {system_name}",
                'result'  : { "error" : text }
            }
        return response

class StatusSystemResource(TychoResource):
    """ Status executing systems. """
    def post(self):
        """
        Status running systems.
        ---
        tag: start
        description: Status running systems.
        requestBody:
            description: List systems.
            required: true
            content:
                application/json:
                    schema:
                        $ref: '#/components/schemas/StatusRequest'
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
        response = {}
        try:
            logging.debug (f"list-request: {json.dumps(request.json, indent=2)}")
            self.validate (request, component="StatusRequest") 
            system_name = request.json.get('name', None)
            response = {
                'status'  : 'success',
                'result'  : get_compute().status (system_name),
                'message' : f"Status system: {system_name}"
            }
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            text = traceback.format_exception(exc_type, exc_value, exc_traceback)
            app.logger.debug (''.join (text))
            response = {
                'status' : "error",
                'message': f"Failed to get system status",
                'result' : { "error" : text }
            }
        print (json.dumps (response, indent=2))
        return response

""" Register endpoints. """
api.add_resource(StartSystemResource, '/system/start')
api.add_resource(StatusSystemResource, '/system/status')
api.add_resource(DeleteSystemResource, '/system/delete')

if __name__ == "__main__":
   parser = argparse.ArgumentParser(description='Tycho Distributed Compute API')
   parser.add_argument('-b', '--backplane', help='Compute backplane type.', default="kubernetes")
   parser.add_argument('-p', '--port',  type=int, help='Port to run service on.', default=5000)
   parser.add_argument('-d', '--debug', help="Debug log level.", default=False, action='store_true')

   args = parser.parse_args ()

   """ Configure the compute back end. """
   if not ComputeFactory.is_valid_backplane (args.backplane):
       print (f"Unrecognized backplane value: {args.backplane}.")
       print (f"Supported backplanes: {supported_backplanes}")
       parser.print_help ()
       sys.exit (1)
   if args.debug:
       debug = True
       logging.basicConfig(level=logging.DEBUG)
   app.run(debug=args.debug)
   app.run(host='0.0.0.0', port=args.port, debug=True, threaded=True)
