import numpy as np


class Dataslot(object):
    """Handles datasets in a pipeline"""
    _instance_counter = 0
    _instances = {}

    def __init__(self, path, identifier=None, name=None):
        Dataslot._instance_counter += 1
        self.path = path
        if identifier is None:
            identifier = "Dataslot_{}".format(Dataslot._instance_counter)
            while identifier in Dataslot._instances:
                Dataslot._instance_counter += 1
                identifier = "Dataslot_{}".format(Dataslot._instance_counter)

        if name is None:
            name = identifier
        #: unique identifier of the filter
        self.identifier = identifier
        #: user-defined name of the filter
        self.name = name
        if identifier in Dataslot._instances:
            raise ValueError("Dataslot with identifier "
                             + "'{}' already exists!".format(identifier))
        Dataslot._instances[identifier] = self
        self.color = random_color()

    def __getstate__(self):
        state = {"color": self.color,
                 "name": self.name,
                 "path": self.path,
                 }
        return state

    def __setstate__(self, state):
        self.color = state["color"]
        self.name = state["name"]
        self.path = state["path"]


def random_color():
    color = "#"
    for _ in range(3):
        # dark colors (until 200)
        color += hex(np.random.randint(0, 200))[2:]
    # alpha
    color += "FF"
    return color.upper()
