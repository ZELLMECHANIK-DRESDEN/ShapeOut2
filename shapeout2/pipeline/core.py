import dclab
from dclab.rtdc_dataset.fmt_hierarchy import RTDC_Hierarchy
import numpy as np

from .. import meta_tool
from .. import util

from .dataslot import Dataslot
from .filter import Filter
from .plot import Plot


class Pipeline(object):
    def __init__(self, state=None):
        self.reset()
        #: Analysis matrix with dataset hierarchies. The first index
        #: identifies the slot and the second index identifies the
        #: filter
        self.matrix = []
        #: used for detecting changes in the matrix
        self._matrix_hash = "None"
        #: holds the slot identifiers of the current matrix
        self._matrix_slots = []
        #: holds the filter identifiers of the current matrix
        self._matrix_filters = []
        #: previous state (see __setstate__)
        self._old_state = {}
        if state is not None:
            self.__setstate__(state)

    def __setstate__(self, state):
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
        self.element_states = state["elements"]

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
        filt: shapeout2.pipeline.Filter
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

    def add_plot(self, plot=None):
        """Add a filter to the pipeline

        Parameters
        ----------
        plot: shapeout2.pipeline.Plot
            plot to generate

        Returns
        -------
        index: int
            index of the plot in the pipeline;
            indexing starts at "0".
        """
        if plot is None:
            plot = Plot()
        self.plots.append(plot)
        return plot.identifier

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
        # TODO:
        # - incremental updates
        matrix_filters = [filt.identifier for filt in self.filters]
        matrix_slots = [slot.identifier for slot in self.slots]
        matrix_hash = util.hashobj([matrix_slots, matrix_filters])
        n_filt_then = len(self._matrix_filters)
        if self._matrix_hash != matrix_hash:
            matrix = []
            if self._matrix_filters == matrix_filters:
                # only a slot was added/removed
                for sl in self.slots:
                    # find it in the old matrix
                    for row in self.matrix:
                        if row[0].identifier == sl.identifier:
                            # use this row
                            break
                    else:
                        # new dataset
                        ds = dclab.new_dataset(sl.path,
                                               identifier=sl.identifier)
                        row = [ds]
                        for _ in self.filters:
                            # generate hierarchy children
                            ds = RTDC_Hierarchy(hparent=ds,
                                                apply_filter=False)
                            row.append(ds)
                    matrix.append(row)
            elif (self._matrix_slots == matrix_slots
                  and self._matrix_filters == matrix_filters[:n_filt_then]):
                # only a filter was added
                matrix = self.matrix
                for ii, sl in enumerate(self.slots):
                    row = matrix[ii]
                    for _ in self.filters[n_filt_then:]:
                        ds = RTDC_Hierarchy(hparent=row[-1],
                                            apply_filter=False)
                        row.append(ds)
            else:
                # everything changed
                for sl in self.slots:
                    ds = dclab.new_dataset(sl.path, identifier=sl.identifier)
                    row = [ds]
                    for _ in self.filters:
                        # generate hierarchy children
                        ds = RTDC_Hierarchy(hparent=ds,
                                            apply_filter=False)
                        row.append(ds)
                    matrix.append(row)

            self.matrix = matrix
            self._matrix_hash = matrix_hash
            self._matrix_slots = matrix_slots
            self._matrix_filters = matrix_filters
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
            # TODO:
            # - cache previously filter states and compare to new filter
            #   states to avoid recomputation when `apply_filter`
            #   is called.
            # these are the element states in gui.matrix.dm_element
            if fstates[filt_id]:
                filt.update_dataset(row[ii])
            else:
                row[ii].config["filtering"]["enable filters"] = False
        dsend = row[filt_index]
        if apply_filter:
            dsend.apply_filter()
        return dsend

    def get_min_max(self, feat):
        fmin = np.inf
        fmax = -np.inf
        for slot_index in range(self.num_slots):
            ds = self.get_dataset(slot_index=slot_index,
                                  filt_index=0,
                                  apply_filter=False)
            vmin = np.nanmin(ds[feat])
            vmax = np.nanmax(ds[feat])
            fmin = np.min([fmin, vmin])
            fmax = np.max([fmax, vmax])
        return fmin, fmax

    def get_features(self, scalar=False, label_sort=False):
        """Return a list of features that all slots share"""
        if scalar:
            features = dclab.dfn.scalar_feature_names
        else:
            features = dclab.dfn.feature_names
        for slot_index in range(self.num_slots):
            ds = self.get_dataset(slot_index=slot_index,
                                  filt_index=0,
                                  apply_filter=False)
            features = sorted(set(ds.features) & set(features))
        if label_sort:
            labs = [dclab.dfn.feature_name2label[f] for f in features]
            lf = sorted(zip(labs, features))
            features = [it[1] for it in lf]
        return features

    def reset(self):
        """Reset the pipeline"""
        #: Filters are instances of :class:`shapeout2.pipeline.Filter`
        self.filters = []
        #: Plots are instances of :class:`shapeout2.pipeline.Plot`
        self.plots = []
        #: Slots are instances of :class:`shapeout2.pipeline.Dataslot`
        self.slots = []
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
