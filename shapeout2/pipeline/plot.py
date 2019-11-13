import copy
import warnings

import dclab


DEFAULT_STATE = {
    "layout": {
        "column count": 3,
        "division": "each",
        "legend": True,  # display plot legend
        "name": "no default",  # overridden by __init__
        "show event count": True,  # display event count
        "size x": 500,
        "size y": 400,
    },
    "general": {
        "axis x": "area_um",
        "axis y": "deform",
        "isoelastics": True,  # display isoelasticity lines
        "kde": "histogram",  # see dclab.kde_methods.methods
        "range x": [0, 500],
        "range y": [0, 0.2],
        "scale x": "linear",
        "scale y": "linear",
    },
    "scatter": {
        "downsample": True,
        "downsampling value": 5000,
        "enabled": True,
        "marker hue": "kde",  # hue defined by: kde, dataset, feature, none
        "marker size": 3.0,  # marker size [pt]
        "hue feature": "bright_avg",  # which feature to use, if set
        "colormap": "jet",  # only applies when hue is "kde" or "feature"
    },
    "contour": {
        "enabled": True,
        "percentiles": [95.0, 50.0],
        "line widths": [3.0, 1.5],  # contour line widths [pt]
        "line styles": ["solid", "dashed"],
        "spacing x": 2,  # spacing for "axis x" and linear "scale x"
        "spacing y": 0.005,  # spacing for "axis y" and linear "scale y"
    }
}

_kde_methods = sorted(dclab.kde_methods.methods.keys())
_kde_methods.remove("none")  # does not make sense here

STATE_OPTIONS = {
    "layout": {
        "column count": int,
        "division": ["each", "merge", "multiscatter+contour"],
        "legend": bool,
        "name": str,
        "show event count": bool,
        "size x": float,
        "size y": float, },
    "general": {
        "axis x": dclab.dfn.scalar_feature_names,
        "axis y": dclab.dfn.scalar_feature_names,
        "isoelastics": bool,
        "kde": _kde_methods,
        "range x": (float,),
        "range y": (float,),
        "scale x": ["linear", "log"],
        "scale y": ["linear", "log"],
    },
    "scatter": {
        "downsampling": bool,
        "downsampling value": int,
        "enabled":  bool,
        "marker hue": ["dataset", "kde", "feature", "none"],
        "marker size": float,
        "hue feature": dclab.dfn.scalar_feature_names,
        "colormap": ["jet"],
    },
    "contour": {
        "enabled":  bool,
        "percentiles": (float,),
        "line widths": (float,),
        "line styles": (["solid", "dashed", "dotted"],),
        "spacing x": float,
        "spacing y": float,
    }
}


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

        # initially, set default state
        self._state = copy.deepcopy(DEFAULT_STATE)

        if name is None:
            name = identifier
        #: unique identifier of the plot
        self.identifier = identifier
        #: user-defined name of the plot
        self.name = name
        if identifier in Plot._instances:
            raise ValueError("Plot with identifier "
                             + "'{}' already exists!".format(identifier))
        Plot._instances[identifier] = self

    @property
    def name(self):
        return self._state["layout"]["name"]

    @name.setter
    def name(self, value):
        self._state["layout"]["name"] = value

    def __getstate__(self):
        return self._state

    def __setstate__(self, state):
        self._state = state

    @staticmethod
    def get_instances():
        return Plot._instances

    @staticmethod
    def get_plot(identifier):
        """Get the plot with the given identifier.

        Notes
        -----
        Creates the plot if it does not exist.
        """
        if identifier in Plot._instances:
            f = Plot._instances[identifier]
        else:
            f = Plot(identifier=identifier)
        return f

    @property
    def hash(self):
        """Return the hash of the plot"""
        warnings.warn("Plot hashing not implemented yet!")
        return self.identifier
