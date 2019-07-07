import datetime
import json
import os
import traceback
import yaml
from jinja2 import Template

class TemplateUtils:
    def render (self, template, context):
        result=None
        template_path = os.path.join (os.path.dirname (__file__), "template", template)
        with open(template_path, "r") as stream:
            template_text = stream.read ()
            result = self.render_text (template_text, context)
        return result
    def render_text (self, template_text, context):
        template = Template (template_text)
        template.globals['now'] = datetime.datetime.utcnow
        text = template.render (**context)
        return yaml.load (text)
