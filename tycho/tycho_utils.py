import datetime
import json
import os
import traceback
import yaml
from jinja2 import Template

class TemplateUtils:
    def render (self, template, context):
        template_path = os.path.join (os.path.dirname (__file__), "template", template)
        self.template = None
        with open(template_path, "r") as stream:
            self.template = Template (stream.read ())
        self.template.globals['now'] = datetime.datetime.utcnow
        text = self.template.render (**context)
        return yaml.load (text)
