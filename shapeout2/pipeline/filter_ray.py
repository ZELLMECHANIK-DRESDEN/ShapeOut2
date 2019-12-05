import dclab


class FilterRay(object):
    def __init__(self, slot):
        """Manages filter-based dataset hierarchies

        Filter rays are used to cache RTDCBase filter-hierarchy
        children.
        """
        #: identifier of the ray (matches the slot)
        self.identifier = slot.identifier
        #: slot defining the ray
        self.slot = slot
        #: list of RTDCBase (hierarchy children)
        self.steps = []
        #: corresponds to hashes of the applied filters
        self.step_hashes = []
        # used for checking validity of the ray
        self._slot_hash = "unset"
        self._verify_slot()
        self._root_child = None

    def _add_step(self, filt, ds):
        """Add a filter step"""
        self.step_hashes.append(filt.hash)
        filt.update_dataset(ds)
        self.steps.append(ds)
        identifier = self.slot.identifier + "-" + filt.identifier + "-child"
        ds = dclab.rtdc_dataset.RTDC_Hierarchy(
            ds, apply_filter=False, identifier=identifier)
        return ds

    def _verify_slot(self):
        """Reset things if necessary"""
        # TODO: Is this really necessary because of emodulus recomputation?
        if self.slot.hash != self._slot_hash:
            self.steps = []
            self.step_hashes = []
            self._slot_hash = self.slot.hash

    @property
    def root_child(self):
        if self._root_child is None:
            ds = self.slot.get_dataset()
            identifier = self.slot.identifier + "-root"
            self._root_child = dclab.rtdc_dataset.RTDC_Hierarchy(
                ds, apply_filter=True, identifier=identifier)
        return self._root_child

    def get_dataset(self, filters, apply_filter=True):
        """Return the dataset that corresponds to applying these filters"""
        # make sure the slot did not change
        self._verify_slot()

        # only take into account active filters
        filters = [f for f in filters if f.filter_used]

        ds = self.root_child

        if filters:
            for ii, filt in enumerate(filters):
                if len(self.steps) < ii+1:
                    # just create a new step
                    ds = self._add_step(filt, ds)
                elif filt.hash != self.step_hashes[ii]:
                    # the filter ray is changing here;
                    # cut it and add a new step
                    self.steps = self.steps[:ii]
                    self.step_hashes = self.step_hashes[:ii]
                    ds = self._add_step(filt, ds)
                else:
                    # the filters match so far
                    ds = self.steps[ii]
            # we now have the entire filter pipeline in self.steps
            final_ds = self.steps[ii]  # not -1, the ray might be longer
            if apply_filter:
                final_ds.apply_filter()
        else:
            final_ds = ds
        return final_ds
