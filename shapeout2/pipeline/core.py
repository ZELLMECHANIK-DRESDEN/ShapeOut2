import copy
import warnings

import dclab
from dclab.rtdc_dataset.fmt_hierarchy import RTDC_Hierarchy
import numpy as np

from .dataslot import Dataslot
from .filter import Filter
from .filter_ray import FilterRay
from .plot import Plot


class Pipeline(object):
    def __init__(self, state=None):
        self.reset()
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
        for filt_state in state["filters"]:
            self.add_filter(filt_state)
        for plot_state in state["plots"]:
            self.add_plot(plot_state)
        for slot_state in state["slots"]:
            self.add_slot(slot=slot_state)
        # set element states at the end
        self.element_states = state["elements"]

        # sanity checks
        if set(self.filters_used) != set(state["filters used"]):
            raise ValueError("Bad pipeline state ('filters used' don't match)")
        if set(self.slots_used) != set(state["slots used"]):
            raise ValueError("Bad pipeline state ('slots used' don't match)")

    def __getstate__(self):
        state = {}
        state["elements"] = copy.deepcopy(self.element_states)
        state["filters"] = [filt.__getstate__() for filt in self.filters]
        state["filters used"] = self.filters_used
        state["plots"] = [plot.__getstate__() for plot in self.plots]
        state["slots"] = [slot.__getstate__() for slot in self.slots]
        state["slots used"] = self.slots_used
        return state

    @property
    def filter_ids(self):
        return [filt.identifier for filt in self.filters]

    @property
    def filters_used(self):
        return [filt.identifier for filt in self.filters if filt.filter_used]

    @property
    def plot_ids(self):
        return [plot.identifier for plot in self.plots]

    @property
    def slot_ids(self):
        return [slot.identifier for slot in self.slots]

    @property
    def slots_used(self):
        return [slot.identifier for slot in self.slots if slot.slot_used]

    @property
    def num_filters(self):
        return len(self.filters)

    @property
    def num_plots(self):
        return len(self.filters)

    @property
    def num_slots(self):
        return len(self.slots)

    @property
    def paths(self):
        return [ds.path for ds in self.slots]

    def add_filter(self, filt=None, index=None):
        """Add a filter to the pipeline

        Parameters
        ----------
        filt: shapeout2.pipeline.Filter or dict
            Filter instance or its state from Filter.__getstate__()
        index: int
            Position in the filter list, defaults to `len(self.filters)`

        Returns
        -------
        index: int
            index of the filter in the pipeline;
            indexing starts at "0".
        """
        if index is None:
            index = len(self.filters)
        if filt is None:
            filt = Filter()
        elif isinstance(filt, Filter):
            pass
        elif isinstance(filt, dict):
            state = filt
            if state["identifier"] in Filter._instances:
                filt = Filter._instances[filt["identifier"]]
            else:
                filt = Filter()
            filt.__setstate__(state)
        self.filters.insert(index, filt)
        filt_id = filt.identifier
        for slot_id in self.slot_ids:
            self.element_states[slot_id][filt_id] = False
        return filt_id

    def add_plot(self, plot=None, index=None):
        """Add a plot to the pipeline

        Parameters
        ----------
        plot: shapeout2.pipeline.Plot or dict
            Plot instance or its state from Plot.__getstate__()
        index: int
            Position in the plot list, defaults to `len(self.plots)`

        Returns
        -------
        index: int
            index of the plot in the pipeline;
            indexing starts at "0".
        """
        if index is None:
            index = len(self.plots)
        if plot is None:
            plot = Plot()
        elif isinstance(plot, Plot):
            pass
        elif isinstance(plot, dict):
            state = plot
            if state["identifier"] in Plot._instances:
                plot = Plot._instances[plot["identifier"]]
            else:
                plot = Plot()
            plot.__setstate__(state)

        self.plots.insert(index, plot)
        plot_id = plot.identifier
        for slot_id in self.slot_ids:
            self.element_states[slot_id][plot_id] = False

        return plot.identifier

    def add_slot(self, slot=None, path=None, index=None):
        """Add a slot (experiment) to the pipeline

        Parameters
        ----------
        slot: shapeout2.pipeline.Dataslot or dict
            Dataslot representing an experimental dataset or its
            state from Dataslot.__getstate__(); At least `slot`
            or `path` need to be specified
        path: str or pathlib.Path
            Path to a measurement
        index: int
            Position in the slot list, defaults to `len(self.slots)`

        Returns
        -------
        index: int
            index of the slot in the pipeline;
            indexing starts at "0".
        identifier: str
            identifier of the slot
        """
        if index is None:
            index = len(self.slots)
        if ((slot is None and path is None)
                or (slot is not None and path is not None)):
            raise ValueError("Please specify either `slot` or `path`.")
        elif path is not None:
            slot = Dataslot(path=path)
        elif isinstance(slot, Dataslot):
            pass
        elif isinstance(slot, dict):
            state = slot
            if state["identifier"] in Dataslot._instances:
                slot = Dataslot._instances[slot["identifier"]]
            else:
                slot = Dataslot()
            slot.__setstate__(state)

        self.slots.insert(index, slot)
        slot_id = slot.identifier
        self.element_states[slot_id] = {}
        for filt_id in self.filter_ids:
            self.element_states[slot_id][filt_id] = False
        for plot_id in self.plot_ids:
            self.element_states[slot_id][plot_id] = False
        return slot.identifier

    def apply_filter_ray(self, rtdc_ds, slot_id):
        """Convenience function for applying filters to other data

        The filters that are currently set for a specific slot with
        `slot_id` are applied to a dataset.

        Parameters
        ----------
        rtdc_ds: dclab.rtdc_dataset.RTDCBase
            Dataset
        slot_id: str
            Identifier of the slot from which the filters are taken
        """
        fstates = self.element_states[slot_id]
        # keeps track of all datasets (useful for debugging)
        datasets = []
        ds = rtdc_ds
        for filt in self.filters:
            filt_id = filt.identifier
            if fstates[filt_id] and filt_id in self.filters_used:
                filt.update_dataset(ds)
            else:
                ds.config["filtering"]["enable filters"] = False
            datasets.append(ds)
            # generate next hierarchy child
            ds = RTDC_Hierarchy(hparent=ds, apply_filter=True)
        return ds

    def get_dataset(self, slot_index, filt_index=-1, apply_filter=True):
        """Return dataset with all filters updated (optionally applied)

        Parameters
        ----------
        slot_index: int
            index of measurement
        filt_index: int or None
            index of filter; if None, then the plain dataset is returned.
            If negative (default), then the last dataset in the pipeline
            is returned (all selected filters applied).
        apply_filter: bool
            whether to call `dataset.apply_filter` in the end;
            if set to `False`, only the filtering configuration
            of the dataset and its hierarchy parents are updated
        ret_color: bool
            also return the color of the dataset as a string
        """
        slot = self.slots[slot_index]
        if filt_index is None or (filt_index == -1 and len(self.slots) == 0):
            # return the unfiltered dataset
            ds = slot.get_dataset()
        else:
            if filt_index < 0:
                filt_index = len(self.filters) - 1
            slot_id = slot.identifier
            # the filters used
            filters = []
            for filt_id in self.filter_ids[:filt_index+1]:
                if (self.is_element_active(slot_id, filt_id)
                        and filt_id in self.filters_used):
                    filters.append(self.get_filter(filt_id))
            # filter ray magic
            ray = self.get_ray(slot.identifier)
            ds = ray.get_dataset(filters, apply_filter=apply_filter)
        return ds

    def get_datasets(self, filt_index=-1, apply_filter=True):
        """Return all datasets with filters applied

        The parameters are passed to :func:`Pipeline.get_dataset`.
        """
        kw = {"filt_index": filt_index,
              "apply_filter": apply_filter}
        return [self.get_dataset(ii, **kw) for ii in range(len(self.slots))]

    def get_features(self, scalar=False, label_sort=False, union=False,
                     plot_id=None):
        """Return a list of features in the pipeline

        Parameters
        ----------
        scalar: bool
            If True, only return scalar features
        label_sort: bool
            If True, return the features sorted by label
            instead of by feature name
        union: bool
            If True, return the union of features available in all
            slots. If False (default), return only those features
            that are shared by all slots.
        plot_id: None or str
            If set, only datasets that are part of the matching Plot
            instance are used. If None, all datasets of the pipeline
            are used.
        """
        if scalar:
            base_features = dclab.dfn.scalar_feature_names
        else:
            base_features = dclab.dfn.feature_names
        if union:
            features = set()
        else:
            features = set(base_features)
        for slot_index in range(self.num_slots):
            slot_id = self.slot_ids[slot_index]
            if (plot_id is None
                or (self.element_states[slot_id][plot_id]
                    and slot_id in self.slots_used)):
                ds = self.get_dataset(slot_index=slot_index, filt_index=None)
                ds_features = set(ds.features) & set(base_features)
                if union:
                    features |= ds_features
                else:
                    features &= ds_features
        if label_sort:
            labs = [dclab.dfn.feature_name2label[f] for f in features]
            lf = sorted(zip(labs, features))
            features = [it[1] for it in lf]
        else:
            features = sorted(features)
        return features

    def get_filter(self, filt_id):
        """Return the Filter matching the identifier"""
        if filt_id not in self.filter_ids:
            raise ValueError(
                "Filter '{}' not part of this pipeline!".format(filt_id))
        return self.filters[self.filter_ids.index(filt_id)]

    def get_min_max(self, feat, plot_id=None, margin=0.0):
        """Return minimum and maximum values for a feature

        Parameters
        ----------
        feat: str
            Feature name
        plot_id: str
            Plot identifier
        margin: float
            Fraction by which the minimum and maximum are
            extended. E.g. for plotting with a 5% margin
            use `margin=0.05`.
        """
        if plot_id is not None:
            dslist = self.get_plot_datasets(plot_id)[0]
        else:
            dslist = self.get_datasets(filt_index=None, apply_filter=False)
        fmin = np.inf
        fmax = -np.inf
        for ds in dslist:
            if feat in ds:
                vmin = np.nanmin(ds[feat][ds.filter.all])
                vmax = np.nanmax(ds[feat][ds.filter.all])
                fmin = np.min([fmin, vmin])
                fmax = np.max([fmax, vmax])
            else:
                warnings.warn("Dataset {} does ".format(ds.identifier)
                              + "not contain the feature '{}'!".format(feat))
        if margin:
            diff = fmax - fmin
            fmin -= margin*diff
            fmax += margin*diff

        return [fmin, fmax]

    def get_plot(self, plot_id):
        if plot_id not in self.plot_ids:
            raise ValueError(
                "Plot '{}' not part of this pipeline!".format(plot_id))
        return self.plots[self.plot_ids.index(plot_id)]

    def get_plot_datasets(self, plot_id, apply_filter=True):
        """Return a list of datasets with slot states that belong to a plot"""
        datasets = []
        states = []
        # keep the same order as in self.slots
        for slot_index in range(len(self.slots)):
            slot = self.slots[slot_index]
            slot_id = slot.identifier
            if (self.element_states[slot_id][plot_id]
                    and slot_id in self.slots_used):
                ds = self.get_dataset(slot_index=slot_index,
                                      apply_filter=apply_filter)
                datasets.append(ds)
                states.append(slot.__getstate__())
        return datasets, states

    def get_plot_col_row_count(self, plot_id, pipeline_state=None):
        """Compute how many rows a plot layout requires

        Parameters
        ----------
        plot_id: str
            identifier of a plot in this pipeline
        pipeline_state: dict
            pipeline state to use; defaults to the current pipeline
            state
        """
        if pipeline_state is None:
            pipeline_state = self.__getstate__()

        # plot state
        for pstate in pipeline_state["plots"]:
            if plot_id == pstate["identifier"]:
                break
        else:
            raise KeyError(
                "Plot '{}' not given in pipeline state!".format(plot_id))

        # number of datasets in that plot
        num_scat = 0
        for slot_id in pipeline_state["elements"]:
            num_scat += pipeline_state["elements"][slot_id][plot_id]

        # additional plots
        div = pstate["layout"]["division"]
        if div == "each":
            num_plots = num_scat
        elif div == "merge":
            num_plots = 1
        elif div == "multiscatter+contour":
            num_plots = num_scat + 1
        else:
            raise ValueError("Unrecognized division: '{}'".format(div))

        # column count
        col_count = min(pstate["layout"]["column count"], num_plots)

        # row count
        row_count = int(np.ceil(num_plots/col_count))
        return col_count, row_count

    def get_ray(self, slot_id):
        """Convenience function that creates and returns a filter ray"""
        # cleanup (just in case)
        for key in list(self.rays.keys()):
            if key not in self.slot_ids:
                self.rays.pop(key)
        if slot_id not in self.rays:
            self.rays[slot_id] = FilterRay(self.get_slot(slot_id))
        return self.rays[slot_id]

    def get_slot(self, slot_id):
        """Return the Dataslot matching the RTDCBase identifier"""
        slot_id = slot_id.split("-")[0]  # this is how FilterRay names children
        if slot_id in self.slot_ids:
            slot = self.slots[self.slot_ids.index(slot_id)]
        else:
            raise ValueError("Unknown dataset identifier: "
                             + "`{}`".format(slot_id))
        return slot

    def is_element_active(self, slot_id, filt_plot_id):
        return self.element_states[slot_id][filt_plot_id]

    def remove_filter(self, filt_id):
        """Remove a filter by filter identifier"""
        index = self.filter_ids.index(filt_id)
        self.filters.pop(index)
        for slot_id in self.element_states:
            if filt_id in self.element_states[slot_id]:
                self.element_states[slot_id].pop(filt_id)

    def remove_plot(self, plot_id):
        """Remove a filter by plot identifier"""
        index = self.plot_ids.index(plot_id)
        self.plots.pop(index)
        for slot_id in self.element_states:
            if plot_id in self.element_states[slot_id]:
                self.element_states[slot_id].pop(plot_id)

    def remove_slot(self, slot_id):
        """Remove a slot by slot identifier"""
        index = self.slot_ids.index(slot_id)
        self.slots.pop(index)
        if slot_id in self.element_states:
            self.element_states.pop(slot_id)

    def reset(self):
        """Reset the pipeline"""
        #: Filters are instances of :class:`shapeout2.pipeline.Filter`
        self.filters = []
        #: Plots are instances of :class:`shapeout2.pipeline.Plot`
        self.plots = []
        #: Filter rays of the current pipeline
        self.rays = {}
        #: Slots are instances of :class:`shapeout2.pipeline.Dataslot`
        self.slots = []
        #: individual element states
        self.element_states = {}

    def set_element_active(self, slot_id, filt_plot_id, active=True):
        """Activate an element in the block matrix"""
        self.element_states[slot_id][filt_plot_id] = active
