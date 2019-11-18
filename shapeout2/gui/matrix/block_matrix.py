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
        if self._old_state == state:
            return
        else:
            self._old_state = state
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

    def on_matrix_changed(self):
        state = self.__getstate__()
        self.pipeline_changed.emit(state)
