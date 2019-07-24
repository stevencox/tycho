import datetime
import json
import logging
import netifaces
import os
import string
import traceback
import yaml
from jinja2 import Template

logger = logging.getLogger (__name__)

class TemplateUtils:
    """ Utilities for generating text. """
    
    def render (self, template, context):
        """Render a template object given a context. """
        result=None
        template_path = os.path.join (os.path.dirname (__file__), "template", template)
        with open(template_path, "r") as stream:
            template_text = stream.read ()
            result = self.render_text (template_text, context)
        return result
    def render_text (self, template_text, context):
        """ Render the text of a template given a context. """
        template = Template (template_text)
        template.globals['now'] = datetime.datetime.utcnow
        text = template.render (**context)
        return yaml.load (text)

    @staticmethod
    def apply_environment (environment, text):
        """ Given an environment configuration consisting of lines of Bash style variable assignemnts,
        parse the variables and apply them to the given text."""
        resolved = text
        if environment:
            mapping = {
                line.split("=", maxsplit=1)[0] : line.split("=", maxsplit=1)[1]
                for line in environment.split ("\n") if '=' in line
            }
            resolved = string.Template(text).safe_substitute (**mapping)
            logger.debug (f"environment={json.dumps (mapping, indent=2)}")
            logger.debug (resolved)
        return resolved

    @staticmethod
    def trunc (a_string, max_len=80):
        return (a_string[:max_len] + '..') if len(a_string) > max_len else a_string

class NetworkUtils:
    @staticmethod
    def get_client_ip (request, debug=False):
        """ Get the IP address of the client. Account for requests from proxies. 
        In debug mode, ignore loopback and try to get an IP from a n interface."""
        ip_addr = request.remote_addr
        if request.headers.getlist("X-Forwarded-For"):
            ip_addr = request.headers.getlist("X-Forwarded-For")[0]
        if debug:
            interface = netifaces.ifaddresses ('en0')
            ip_addr = interface[2][0]['addr']
        logger.debug (f"(debug mode ip addr:)--> {ip_addr}")
        return ip_addr
