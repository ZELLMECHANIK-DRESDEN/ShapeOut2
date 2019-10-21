class Plot(object):
    """Handles plotting information in a pipeline"""
    _instance_counter = 0
    _instances = {}

    def __init__(self, identifier=None, name=None):
        Plot._instance_counter += 1
        if identifier is None:
            identifier = "Plot_{}".format(Plot._instance_counter)
            while identifier in Plot._instances:
                Plot._instance_counter += 1
                identifier = "Plot_{}".format(Plot._instance_counter)

        if name is None:
            name = identifier
        #: unique identifier of the filter
        self.identifier = identifier
        #: user-defined name of the filter
        self.name = name
        if identifier in Plot._instances:
            raise ValueError("Plot with identifier "
                             + "'{}' already exists!".format(identifier))
        Plot._instances[identifier] = self
