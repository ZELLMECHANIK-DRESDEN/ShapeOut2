"""Keep record of all filters used"""
import warnings


import dclab


class Filter(object):
    """Handles filters in a pipeline"""
    _instance_counter = 0
    _instances = {}

    def __init__(self, identifier=None, name=None):
        Filter._instance_counter += 1
        if identifier is None:
            identifier = "Filter_{}".format(Filter._instance_counter)
        if name is None:
            name = identifier
        #: unique identifier of the filter
        self.identifier = identifier
        #: user-defined name of the filter
        self.name = name
        #: general filtering arguments are directly passed to
        #: :class:`dclab.filter.Filter`
        self.general = {"remove invalid events": False,  # removes nan/inf
                        "enable filters": True,  # whether to use the filter
                        "limit events": 0,  # "0" means disabled
                        }
        #: box filters with features as keys; each item is a
        #: dictionary with the keys "min", "max", "active"
        self.boxdict = {}
        #: polygon filter list; each item is an instance of
        #: :class:`dclab.PolygonFilter`
        self.polylist = []
        Filter._instances[identifier] = self

    @staticmethod
    def get_filter(identifier):
        """Get the filter with the given identifier.

        Notes
        -----
        Creates the filter if it does not exist.
        """
        if identifier in Filter._instances:
            f = Filter._instances[identifier]
        else:
            f = Filter(identifier=identifier)
        return f

    @property
    def hash(self):
        """Return the hash of the filter"""
        warnings.warn("Filter hashing not implemented yet!")
        return self.identifier

    def add_box_filter(self, feature, min, max, active=True):
        """Add a box filter"""
        if feature not in dclab.dfn.scalar_feature_names:
            raise ValueError("Unknown scalar feature: {}".format(feature))
        self.boxdict[feature] = {
            "min": min,
            "max": max,
            "active": active}

    def apply_to_dataset(self, dataset):
        """Convenience function to apply this filter to a dataset

        Parameters
        ----------
        dataset: :class:`dclab.RTDCBase`
            Input dataset

        Returns
        -------
        filtered_dataset: RTDCBase
            Either the input dataset, or a hierarchy child.

        Notes
        -----

        """
        self.update_dataset(dataset)
        dataset.apply_filter()

    def update_dataset(self, dataset):
        """Update the filtering configuration of a dataset

        Notes
        -----
        Due to the design of the filtering pipeline, it is not
        possible to use manual filters. If any are set, they
        are removed from the filter.
        """
        # remove all previous filters
        dataset.reset_filter()
        cfgfilt = dataset.config["filtering"]

        # set general options
        cfgfilt.update(self.general)

        # set box filters
        for feat in self.boxdict:
            if self.boxdict[feat]["active"]:
                cfgfilt["{} min".format(feat)] = self.boxdict[feat]["min"]
                cfgfilt["{} max".format(feat)] = self.boxdict[feat]["max"]

        # set polygon filters
        for poly in self.polylist:
            dataset.polygon_filter_add(poly)
