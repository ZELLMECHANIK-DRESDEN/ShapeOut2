"""Keep record of all filters used"""
import warnings


class Filter(object):
    _instance_counter = 0
    _instances = {}

    def __init__(self, identifier=None):
        if identifier is None:
            identifier = "Filter_{}".format(Filter._instance_counter)
        self.identifier = identifier
        Filter._instances[identifier] = self

    @property
    def hash(self):
        """Return the hash of the filter"""
        warnings.warn("Filter hashing not implemented yet!")
        return self.identifier

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

    def apply_to(self, dataset):
        """Apply a filter to an instance of RTDCBase

        Parameters
        ----------
        dataset: RTDCBase
            Input dataset

        Returns
        -------
        filtered_dataset: RTDCBase
            Either the input dataset, or a hierarchy child.

        Notes
        -----
        The filter should be applied like so:
        `ds = filter_instance.apply_to(ds)`

        This is necessary to make sure that hierarchy leveling
        filters are applied correctly, i.e. a hierarchy child
        is returned in this case and you want to work with that
        instead of the original dataset.
        """
        warnings.warn("applying filters not yet implemented!")
        return dataset
