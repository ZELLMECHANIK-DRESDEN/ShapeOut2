import copy

from PyQt5 import QtCore, QtWidgets

from .pm_element import MatrixElement
from .pm_plot import MatrixPlot


class PlotMatrix(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(PlotMatrix, self).__init__(parent)

        self.glo = None
        self._reset_layout(init=True)

        # used for toggling between all active, all inactive and semi state
        self.semi_states_plot = {}

    def __getstate__(self):
        """Logical states of the current plot matrix"""
        # plots
        plots = []
        for ps in self.plots:
            plots.append(ps.__getstate__())
        # elements
        mestates = {}
        dm = self.data_matrix
        for ds in dm.datasets:
            idict = {}
            for ps in self.plots:
                me = self.get_matrix_element(ds.identifier, ps.identifier)
                idict[ps.identifier] = me.__getstate__()
            mestates[ds.identifier] = idict
        state = {"elements": mestates,
                 "plots": plots}
        return state

    def __setstate__(self, state):
        self.clear()
        # plot states
        for jj in range(len(state["plots"])):
            ps = self.add_plot()
            ps.__setstate__(state["plots"][jj])
        # make sure elements exist
        self.fill_elements()
        # element states
        for ds_key in state["elements"]:
            ds_state = state["elements"][ds_key]
            for p_key in ds_state:
                el_state = ds_state[p_key]
                el = self.get_matrix_element(ds_key, p_key)
                el.__setstate__(el_state)
        self.adjust_size()

    def _reset_layout(self, init=False):
        if self.glo is not None:
            # send old layout to Nirvana eventually
            layout = self.glo
            self.glo = None
            self.old_layout = QtWidgets.QWidget()
            self.old_layout.setLayout(layout)
            self.old_layout.hide()
            self.old_layout.deleteLater()
        # add new layout
        self.glo = QtWidgets.QGridLayout()
        self.glo.setSpacing(2)
        self.glo.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.glo)
        if not init:
            # This does not work when data_matrix is not ready yet
            self.adjust_size()

    @property
    def data_matrix(self):
        for ch in self.parent().children():
            if ch.__class__.__name__ == "DataMatrix":
                break
        else:
            raise KeyError("DataMatrix not found!")
        return ch

    @property
    def element_width(self):
        """Data matrix element width (without 2px spacing)"""
        return self.data_matrix.element_width

    @property
    def element_height(self):
        """Data matrix element height (without 2px spacing)"""
        return self.data_matrix.element_height

    @property
    def num_datasets(self):
        dm = self.data_matrix
        return dm.num_datasets

    @property
    def num_plots(self):
        count = 0
        for jj in range(self.glo.columnCount()):
            if self.glo.itemAtPosition(0, jj) is not None:
                count += 1
        return count

    @property
    def plots(self):
        plots = []
        for jj in range(self.glo.columnCount()):
            item = self.glo.itemAtPosition(0, jj)
            if item is not None:
                ps = item.widget()
                plots.append(ps)
        return plots

    def add_plot(self):
        name = "PS{}".format(self.num_plots+1)
        mp = MatrixPlot(name)
        mp.option_action.connect(self.on_option_plot)
        mp.active_toggled.connect(self.toggle_plot_active)
        self.glo.addWidget(mp, 0, self.num_plots)
        self.fill_elements()
        self.adjust_size()
        return mp

    def adjust_size(self):
        QtWidgets.QApplication.processEvents()
        ncols = self.num_plots
        nrows = self.data_matrix.num_datasets
        if ncols > 1 and nrows > 1:
            hwidth = self.element_width + 2
            hheight = self.glo.itemAtPosition(0, 1).geometry().height()
            dheight = self.element_height + 2
            self.setMinimumSize(ncols*hwidth,
                                nrows*dheight+hheight)
            self.setFixedSize(ncols*hwidth,
                              nrows*dheight+hheight)

    def clear(self):
        """Reset layout"""
        self._reset_layout()
        self.semi_states_plot = {}

    def fill_elements(self):
        # add widgets
        for ii in range(self.num_datasets):
            for jj in range(self.num_plots):
                if self.glo.itemAtPosition(ii+1, jj) is None:
                    me = MatrixElement()
                    self.glo.addWidget(me, ii+1, jj)
        # make sure enabled/disabled is honored
        dstate = self.data_matrix.__getstate__()
        pstate = self.__getstate__()
        for ds in dstate["datasets"]:
            for ps in pstate["plots"]:
                if not ds["enabled"]:
                    me = self.get_matrix_element(ds["identifier"],
                                                 ps["identifier"])
                    mstate = me.__getstate__()
                    mstate["enabled"] = False
                    me.__setstate__(mstate)

    def get_matrix_element(self, dataset_id, plot_id):
        """Return matrix element matching dataset and plot identifiers"""
        ncols = self.glo.columnCount()
        nrows = self.glo.rowCount()
        for ii in range(1, nrows):
            ds = self.data_matrix.glo.itemAtPosition(ii, 0).widget()
            if ds.identifier == dataset_id:
                for jj in range(ncols):
                    f = self.glo.itemAtPosition(0, jj).widget()
                    if f.identifier == plot_id:
                        break
                else:
                    raise KeyError("Plot '{}' not found!".format(plot_id))
                break
        else:
            raise KeyError("Dataset '{}' not found!".format(dataset_id))
        return self.glo.itemAtPosition(ii, jj).widget()

    @QtCore.pyqtSlot(str)
    def on_option_plot(self, option):
        """Plot option logic (remove, duplicate)"""
        sender = self.sender()
        idx = self.glo.indexOf(sender)
        _, column, _, _ = self.glo.getItemPosition(idx)
        state = self.__getstate__()
        p_state = sender.__getstate__()
        if option == "duplicate":
            p_new = self.add_plot()
            p_state["identifier"] = p_new.identifier
            p_state["title"] += "({})".format(p_new.identifier)
            state["plots"].insert(column+1, p_state)
        else:  # remove
            state["plots"].pop(column)
            for ds_key in state["elements"]:
                state["elements"][ds_key].pop(p_state["identifier"])
        self.__setstate__(state)

    @QtCore.pyqtSlot(bool)
    def toggle_dataset_enable(self, enabled):
        sender = self.sender()
        sid = sender.identifier
        state = self.__getstate__()
        for p_key in state["elements"][sid]:
            # update element widget
            me = self.get_matrix_element(sid, p_key)
            mstate = me.__getstate__()
            mstate["enabled"] = enabled
            me.__setstate__(mstate)

    @QtCore.pyqtSlot()
    def toggle_plot_active(self):
        """Switch between all active, all inactive, previous state

        Modifies the matrix elements for a plot/column,
        which is defined by the signal sender :class:`MatrixPlot`.
        Cyclic toggling order: semi -> all -> none
        """
        self.semi_states_dataset = {}
        sender = self.sender()
        sid = sender.identifier

        states = self.__getstate__()["elements"]
        state = {}
        for key in states:
            state[key] = states[key][sid]

        num_actives = sum([s["active"] for s in state.values()])

        # update state according to the scheme in the docstring
        if num_actives == 0:
            if sid in self.semi_states_plot:
                # use semi state
                oldstate = self.semi_states_plot[sid]
                for key in oldstate:
                    if key in state:
                        state[key] = oldstate[key]
            else:
                # toggle all to active
                for key in state:
                    state[key]["active"] = True
        elif num_actives == len(state):
            # toggle all to inactive
            for key in state:
                state[key]["active"] = False
        else:
            # save semi state
            self.semi_states_plot[sid] = copy.deepcopy(state)
            # toggle all to active
            for key in state:
                state[key]["active"] = True

        for dsid in state:
            me = self.get_matrix_element(dsid, sid)
            me.__setstate__(state[dsid])
