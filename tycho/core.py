from tycho.config import Config
from tycho.factory import ComputeFactory
from tycho.factory import supported_backplanes
from tycho.model import System

class Tycho:
    """ An organizing abstraction for the system. """
    
    def __init__(self,
                 backplane="kubernetes",
                 config="conf/tycho.yaml"):
        """ Construct a Tycho component. """
        self.backplane = backplane
        self.config = Config (config)
        self.compute = ComputeFactory.create_compute ()
        
    def get_compute (self):
        """ Get the Tycho API for the compute fabric. """
        return self.compute

    def parse (self, request):
        """ Parse a request to construct an abstract syntax tree for a system.
        
            :param request: JSON object formatted to contain name, structure, env, and 
                            service elements. Name is a string. Structue is the JSON 
                            object resulting from loading a docker-compose.yaml. Env
                            is a JSON dictionary mapping environment variables to
                            values. These will be substituted into the specification.
                            Services is a JSON object representing which containers and
                            ports to expose, and other networking rules.
            :returns: dict - A `tycho.model.System`
        """
        return System.parse (
            name=request['name'],
            system=request['system'],
            env=request.get ('env', {}),
            services=request.get ('services', {}))
    
    @staticmethod
    def is_valid_backplane (backplane):
        """ Determine if the argument is a valid backplane. """
        return ComputeFactory.is_valid_backplane (backplane)
    
    @staticmethod
    def supported_backplanes ():
        return list(supported_backplanes)
