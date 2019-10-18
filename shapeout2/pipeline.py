import dclab
import numpy as np

from .dataslot import Dataslot
from .filter import Filter
from . import meta_tool
from . import util


class Pipeline(object):
    def __init__(self, state=None):
        self.reset()
        self._matrix_hash = "None"
        self._old_state = {}
        if state is not None:
            self.__setstate__(state)

    def __setstate__(self, state):
        Pipeline._reduce_state(state)
        if self._old_state == state:
            # Nothing changed
            return
        self._old_state = state
        self.reset()
        for ff in state["filters"]:
            if ff["identifier"] in Filter._instances:
                filt = Filter._instances[ff["identifier"]]
            else:
                filt = Filter(identifier=ff["identifier"])
            # Also update filter parameters (for convenience)
            filt.general["enable filters"] = ff["enabled"]
            filt.name = ff["name"]
            self.add_filter(filt)

        for dd in state["datasets"]:
            if dd["identifier"] in Dataslot._instances:
                # use existing slot
                slot = Dataslot._instances[dd["identifier"]]
            else:
                # create new slot
                slot = Dataslot(path=dd["path"],
                                identifier=dd["identifier"])
            self.add_slot(slot=slot)
        self.construct_matrix()
        self.element_states = state["elements"]

    @staticmethod
    def _reduce_state(state):
        """Reduce a state from DataMatrix to something we can work with"""
        for slot_id in state["elements"]:
            for filt_id in state["elements"][slot_id]:
                active = state["elements"][slot_id][filt_id]["active"]
                enabled = state["elements"][slot_id][filt_id]["enabled"]
                state["elements"][slot_id][filt_id] = active and enabled

    @property
    def num_filters(self):
        return len(self.filters)

    @property
    def num_slots(self):
        return len(self.slots)

    @property
    def paths(self):
        return [ds.path for ds in self.slots]

    def add_filter(self, filt=None):
        """Add a filter to the pipeline

        Parameters
        ----------
        filt: shapeout2.filter.Filter
            filter to apply

        Returns
        -------
        index: int
            index of the filter in the pipeline;
            indexing starts at "0".
        """
        if filt is None:
            filt = Filter()
        self.filters.append(filt)
        return filt.identifier

    def add_slot(self, slot=None, path=None):
        """Add a slot (experiment) to the pipeline

        Parameters
        ----------
        slot: Dataslot
            Dataslot representing an experimental dataset

        Returns
        -------
        index: int
            index of the slot in the pipeline;
            indexing starts at "0".
        identifier: str
            identifier of the slot
        """
        if slot is None and path is not None:
            slot = Dataslot(path=path)
        elif isinstance(slot, Dataslot) and path is None:
            pass
        else:
            raise ValueError("Please check arguments")
        self.slots.append(slot)
        # check that the features are all the same
        f0 = meta_tool.get_rtdc_features(self.slots[0].path)
        fi = meta_tool.get_rtdc_features(slot.path)
        if f0 != fi:
            # This is important for updating the filter min/max values
            # TODO:
            # - ignore features that are not shared among all datasets
            raise ValueError("Currently, only RT-DC measurements with the "
                             + "same scalar features are allowed - Sorry. "
                             + "Please create an issue if you need this.")
        return slot.identifier

    def construct_matrix(self):
        """Construct the pipeline matrix

        This generates dataset hierarchies and updates
        the filters.
        """
        matrix_hash = util.hashobj([
            [slot.identifier for slot in self.slots],
            [filt.identifier for filt in self.filters],
            ])
        if self._matrix_hash != matrix_hash:
            self._matrix_hash = matrix_hash
            self.matrix = []
            for sl in self.slots:
                ds = dclab.new_dataset(sl.path)
                row = [ds]
                for _ in self.filters:
                    # generate hierarchy children
                    ds = dclab.new_dataset(ds)
                    row.append(ds)
                self.matrix.append(row)
            # TODO:
            # - if `self.elements_dict` is not complete, autocomplete it
            #   (as it is done in gui.matrix.dm_dataset)

    def get_dataset(self, slot_index, filt_index, apply_filter=True):
        """Return dataset with all filters updated (optionally applied)

        Parameters
        ----------
        slot_index: int
            index of measurement
        filt_index: int
            index of filter
        apply_filter: bool
            whether to call `dataset.apply_filter` in the end;
            if set to `False`, only the filtering configuration
            of the dataset and its hierarchy parents are updated
        """
        self.construct_matrix()
        row = self.matrix[slot_index]
        slot_id = self.slots[slot_index].identifier
        fstates = self.element_states[slot_id]
        # set all necessary filters
        for ii in range(filt_index + 1):
            filt = self.filters[ii]
            filt_id = filt.identifier
            # these are the element states in gui.matrix.dm_element
            if fstates[filt_id]:
                filt.update_dataset(row[ii])
        dsend = row[filt_index]
        if apply_filter:
            dsend.apply_filter()
        return dsend

    def get_min_max(self, feat):
        fmin = np.inf
        fmax = -np.inf
        for ii in range(self.num_slots):
            ds = self.get_dataset(slot_index=ii,
                                  filt_index=0,
                                  apply_filter=False)
            fmin = np.min([fmin, np.nanmin(ds[feat])])
            fmax = np.max([fmax, np.nanmax(ds[feat])])
        return fmin, fmax

    def reset(self):
        """Reset the pipeline"""
        #: Filters are instances of :class:`shapeout2.filter.Filter`
        self.filters = []
        #: Slots are instances of :class:`shapeout2.dataslot.Dataslot`
        self.slots = []
        #: Analysis matrix with dataset hierarchies. The first index
        #: identifies the slot and the second index identifies the
        #: filter
        self.matrix = []
        self._matrix_hash = "None"
        #: individual element states
        self.element_states = {}

    def rm_filter(self, index):
        """Remove a filter by index

        indexing starts at "0"
        """
        self.filters.pop(index)

    def rm_slot(self, index):
        """Remove a slot by index

        indexing starts at "0"
        """
        self.slots.pop(index)
