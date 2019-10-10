class Dataslot(object):
    _instance_counter = 0
    _instances = {}

    """Handles datasets in a pipeline"""

    def __init__(self, path, identifier=None, name=None):
        Dataslot._instance_counter += 1
        self.path = path
        if identifier is None:
            identifier = "Dataslot_{}".format(Dataslot._instance_counter)
        if name is None:
            name = identifier
        #: unique identifier of the filter
        self.identifier = identifier
        #: user-defined name of the filter
        self.name = name

        Dataslot._instances[identifier] = self
