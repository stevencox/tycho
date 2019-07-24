from tycho.config import Config
from tycho.factory import ComputeFactory
from tycho.factory import supported_backplanes
from tycho.model import SystemParser

class Tycho:
    """ An organizing abstraction for the system. """
    
    def __init__(self,
                 backplane="kubernetes",
                 config="conf/tycho.yaml"):
        """ Construct a Tycho component. """
        self.backplane = backplane
        self.config = Config (config)
        self.compute = ComputeFactory.create_compute ()
        self.system_parser = SystemParser ()
        
    def get_compute (self):
        """ Get the Tycho API for the compute fabric. """
        return self.compute
    
    def parse (self, name, structure, settings=None, firewall={}):
        """ Compile the specification into a Tycho system model. """
        return self.system_parser.parse (
            name=name,
            structure=structure,
            settings=settings,
            firewall=firewall)

    @staticmethod
    def is_valid_backplane (backplane):
        """ Determine if the argument is a valid backplane. """
        return ComputeFactory.is_valid_backplane (backplane)
    
    @staticmethod
    def supported_backplanes ():
        return list(supported_backplanes)
