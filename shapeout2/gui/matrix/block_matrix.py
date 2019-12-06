import copy

from PyQt5 import QtCore


class BlockMatrix(QtCore.QObject):
    pipeline_changed = QtCore.pyqtSignal(dict)

    def __init__(self, data_matrix, plot_matrix, *args, **kwargs):
        """Helper class that wraps DataMatrix and PlotMatrix"""
        super(BlockMatrix, self).__init__(*args, **kwargs)
        self.data_matrix = data_matrix
        self.plot_matrix = plot_matrix
        self._old_state = {}
        # Signals
        self.data_matrix.matrix_changed.connect(self.on_matrix_changed)
        self.plot_matrix.matrix_changed.connect(self.on_matrix_changed)

    def __getstate__(self):
        state = self.data_matrix.__getstate__()
        statep = self.plot_matrix.__getstate__()
        state["plots"] = statep["plots"]
        for ss in statep["elements"]:
            for plot in statep["elements"][ss]:
                state["elements"][ss][plot] = statep["elements"][ss][plot]
        return state

    def __setstate__(self, state):
        # DataMatrix
        stated = copy.deepcopy(state)
        stated.pop("plots")
        for slot_state in state["slots"]:
            slot_id = slot_state["identifier"]
            for plot_state in state["plots"]:
                plot_id = plot_state["identifier"]
                stated["elements"][slot_id].pop(plot_id)
        self.data_matrix.__setstate__(stated)
        # PlotMatrix
        statep = copy.deepcopy(state)
        statep.pop("filters")
        statep.pop("filters used")
        statep.pop("slots used")
        for slot_state in state["slots"]:
            slot_id = slot_state["identifier"]
            for filt_state in state["filters"]:
                filt_id = filt_state["identifier"]
                statep["elements"][slot_id].pop(filt_id)
        self.plot_matrix.__setstate__(statep)

    def adopt_pipeline(self, pipeline_state):
        self.__setstate__(pipeline_state)

    def get_widget(self, slot_id=None, filt_plot_id=None):
        """Convenience function for testing"""
        if slot_id is None and filt_plot_id is not None:
            # get a filter or a plot
            w = self.data_matrix.filter_widgets + self.plot_matrix.plot_widgets
            for wi in w:
                if wi.identifier == filt_plot_id:
                    break
            else:
                raise KeyError(
                    "Widget identifier '{}' not found!".format(filt_plot_id))
            return wi
        elif slot_id is not None and filt_plot_id is None:
            # get a slot
            for wi in self.data_matrix.dataset_widgets:
                if wi.identifier == slot_id:
                    break
            else:
                raise KeyError(
                    "Widget identifier '{}' not found!".format(filt_plot_id))
            return wi
        elif slot_id is not None and filt_plot_id is not None:
            # get a matrix element
            wd = self.data_matrix.element_widget_dict
            wp = self.plot_matrix.element_widget_dict
            fpd = wd[slot_id]
            fpp = wp[slot_id]
            if filt_plot_id in fpp:
                wi = fpp[filt_plot_id]
            elif filt_plot_id in fpd:
                wi = fpd[filt_plot_id]
            else:
                raise KeyError(
                    "Widget identifier '{}' not found!".format(filt_plot_id))
            return wi
        else:
            raise ValueError(
                "One of `slot_id` or `filt_plot_id` must be specified!")

    def invalidate_elements(self, invalid_dm, invalid_pm):
        for slot_id, filt_id in invalid_dm:
            em = self.data_matrix.get_matrix_element(slot_id, filt_id)
            em.active = False
            em.invalid = True
            em.update_content()
        for slot_id, plot_id in invalid_pm:
            em = self.plot_matrix.get_matrix_element(slot_id, plot_id)
            em.active = False
            em.invalid = True
            em.update_content()

    def on_matrix_changed(self):
        state = self.__getstate__()
        self.pipeline_changed.emit(state)
