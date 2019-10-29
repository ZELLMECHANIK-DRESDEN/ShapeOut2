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
        self.fl_name_dict = {"fl1": "FL-1",
                             "fl2": "FL-2",
                             "fl3": "FL-3"}

    def __getstate__(self):
        state = {"color": self.color,
                 "name": self.name,
                 "path": self.path,
                 "fl names": self.fl_name_dict,
                 }
        return state

    def __setstate__(self, state):
        self.color = state["color"]
        self.name = state["name"]
        self.path = state["path"]
        self.fl_name_dict = state["fl names"]

    @staticmethod
    def get_slot(identifier):
        """Get the slot with the given identifier.

        Notes
        -----
        Creates the slot if it does not exist.
        """
        if identifier in Dataslot._instances:
            d = Dataslot._instances[identifier]
        else:
            d = Dataslot(identifier=identifier)
        return d

    @staticmethod
    def get_instances():
        return Dataslot._instances


def random_color():
    color = "#"
    for _ in range(3):
        # dark colors (until 200)
        part = hex(np.random.randint(0, 200))[2:]
        if len(part) == 1:
            part += "0"
        color += part
    # alpha
    color += "FF"
    return color.upper()
