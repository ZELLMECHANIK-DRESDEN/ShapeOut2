import dclab
import numpy as np

from .. import meta_tool


class Dataslot(object):
    """Handles datasets in a pipeline"""
    _instance_counter = 0
    _instances = {}

    def __init__(self, path, identifier=None, name=None):
        Dataslot._instance_counter += 1
        self.path = path
        self._dataset = None
        if identifier is None:
            identifier = "Dataslot_{}".format(Dataslot._instance_counter)
            while identifier in Dataslot._instances:
                Dataslot._instance_counter += 1
                identifier = "Dataslot_{}".format(Dataslot._instance_counter)

        if name is None:
            name = meta_tool.get_rtdc_config(path)["experiment"]["sample"]
        #: unique identifier of the filter
        self.identifier = identifier
        #: user-defined name of the filter
        self.name = name
        #: whether or not to use this slot
        self.slot_used = True
        if identifier in Dataslot._instances:
            raise ValueError("Dataslot with identifier "
                             + "'{}' already exists!".format(identifier))
        Dataslot._instances[identifier] = self
        self.color = random_color()
        self.fl_name_dict = {"FL-1": "FL-1",
                             "FL-2": "FL-2",
                             "FL-3": "FL-3"}
        self.config = {
            "crosstalk": {
                # crosstalk
                "crosstalk fl12": 0,
                "crosstalk fl13": 0,
                "crosstalk fl21": 0,
                "crosstalk fl23": 0,
                "crosstalk fl31": 0,
                "crosstalk fl32": 0,
            },
            "emodulus": {
                # emodulus
                "emodulus model": "elastic sphere",
                "emodulus medium": "undefined",
                "emodulus temperature": np.nan,
                "emodulus viscosity": np.nan,
            }
        }

    def __getstate__(self):
        state = {"color": self.color,
                 "crosstalk": self.config["crosstalk"],
                 "emodulus": self.config["emodulus"],
                 "fl names": self.fl_name_dict,
                 "identifier": self.identifier,
                 "name": self.name,
                 "path": self.path,
                 "slot used": self.slot_used,
                 }
        return state

    def __setstate__(self, state):
        if self.identifier != state["identifier"]:
            raise ValueError("Identifier mismatch: '{}' vs. '{}'".format(
                self.identifier, state["identifier"]))
        self.color = state["color"]
        self.config["crosstalk"] = state["crosstalk"]
        self.config["emodulus"] = state["emodulus"]
        self.fl_name_dict = state["fl names"]
        self.name = state["name"]
        self.path = state["path"]
        self.slot_used = state["slot used"]

    @staticmethod
    def get_slot(identifier):
        """Get the slot with the given identifier.
        """
        return Dataslot._instances[identifier]

    @staticmethod
    def get_instances():
        return Dataslot._instances

    def get_dataset(self):
        """Return the corresponding dataset

        Returns
        -------
        ds: dclab.RTDCBase
            Loaded dataset
        """
        if self._dataset is None:
            ds = dclab.new_dataset(self.path, identifier=self.identifier)
            self._dataset = ds
        else:
            ds = self._dataset
        self.update_dataset(ds)
        return ds

    def update_dataset(self, dataset):
        """Update the configuration of an instance of RTDCBase

        This is used to update the configuration for computing
        the Young's modulus and fluorescence crosstalk.
        """
        # emodulus
        medium = self.config["emodulus"]["emodulus medium"]
        temp = self.config["emodulus"]["emodulus temperature"]
        visc = self.config["emodulus"]["emodulus viscosity"]
        if ((medium == "other" and not np.isnan(visc))
            or (medium in dclab.features.emodulus_viscosity.KNOWN_MEDIA
                and not np.isnan(temp))):
            dataset.config["calculation"].update(self.config["emodulus"])
        else:
            # remove any information
            for key in self.config["emodulus"]:
                if key in dataset.config["calculation"]:
                    dataset.config["calculation"].pop(key)
        # crosstalk
        if np.sum(list(self.config["crosstalk"].values())):
            dataset.config["calculation"].update(self.config["crosstalk"])
        else:
            # remove any information
            for key in self.config["crosstalk"]:
                if key in dataset.config["calculation"]:
                    dataset.config["calculation"].pop(key)


def random_color():
    color = "#"
    for _ in range(3):
        # dark colors (until 200)
        part = hex(np.random.randint(0, 200))[2:]
        if len(part) == 1:
            part += "0"
        color += part
    return color.upper()
