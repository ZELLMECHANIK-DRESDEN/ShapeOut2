import copy
import pathlib

from PyQt5 import QtCore, QtWidgets

from .matrix_dataset import MatrixDataset
from .matrix_filter import MatrixFilter
from .matrix_element import MatrixElement


class DataMatrix(QtWidgets.QWidget):
    quickviewed = QtCore.pyqtSignal(pathlib.Path, list)

    def __init__(self, parent=None, analysis=range(3)):
        super(DataMatrix, self).__init__(parent)

        self.glo = None
        self._reset_layout()

        self.setAcceptDrops(True)

        # used for toggling between all active, all inactive and semi state
        self.semi_states_dataset = {}
        self.semi_states_filter = {}

    def __getstate__(self):
        """Logical states of the current data matrix"""
        # datasets
        nrows = self.num_datasets
        datasets = []
        for ii in range(nrows):
            ds = self.glo.itemAtPosition(ii+1, 0).widget()
            datasets.append(ds.__getstate__())
        # filters
        ncols = self.num_filters
        filters = []
        for jj in range(ncols):
            f = self.glo.itemAtPosition(0, jj+1).widget()
            filters.append(f.__getstate__())
        # elements
        mestates = {}
        for si in range(nrows):
            idds = self.glo.itemAtPosition(si+1, 0).widget().identifier
            idict = {}
            for sj in range(ncols):
                idf = self.glo.itemAtPosition(0, sj+1).widget().identifier
                me = self.glo.itemAtPosition(si+1, sj+1).widget()
                idict[idf] = me.__getstate__()
            mestates[idds] = idict
        state = {"elements": mestates,
                 "datasets": datasets,
                 "filters": filters}
        return state

    def __setstate__(self, state):
        self.clear()
        # dataset states
        for ii in range(len(state["datasets"])):
            ds = self.add_dataset(path=None)
            ds.__setstate__(state["datasets"][ii])
        # filter states
        for jj in range(len(state["filters"])):
            f = self.add_filter()
            f.__setstate__(state["filters"][jj])
        # make sure elements exist
        self.fill_elements()
        # element states
        for ds_key in state["elements"]:
            ds_state = state["elements"][ds_key]
            for f_key in ds_state:
                el_state = ds_state[f_key]
                el = self.get_matrix_element(ds_key, f_key)
                el.__setstate__(el_state)

    def _reset_layout(self):
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
        self.adjust_size()

    @property
    def num_datasets(self):
        count = 0
        for ii in range(1, self.glo.rowCount()):
            if self.glo.itemAtPosition(ii, 0) is not None:
                count += 1
        return count

    @property
    def num_filters(self):
        count = 0
        for jj in range(1, self.glo.columnCount()):
            if self.glo.itemAtPosition(0, jj) is not None:
                count += 1
        return count

    def add_dataset(self, path):
        md = MatrixDataset(path)
        self.glo.addWidget(md, self.num_datasets+1, 0)
        md.active_toggled.connect(self.toggle_dataset_active)
        md.option_action.connect(self.on_option_dataset)
        self.fill_elements()
        self.adjust_size()
        return md

    def add_filter(self, evt=None):
        name = "FS{}".format(self.num_filters+1)
        f = MatrixFilter(name)
        f.active_toggled.connect(self.toggle_filter_active)
        self.glo.addWidget(f, 0, self.num_filters+1)
        self.fill_elements()
        self.adjust_size()
        return f

    def adjust_size(self):
        self.update()
        ncols = self.num_filters
        nrows = self.num_datasets
        if ncols > 1 and nrows > 1:
            hwidth = self.glo.itemAtPosition(0, 1).geometry().width() + 2
            hheight = self.glo.itemAtPosition(0, 1).geometry().height() + 2
            dwidth = self.glo.itemAtPosition(1, 0).geometry().width() + 2
            dheight = self.glo.itemAtPosition(1, 0).geometry().height() + 2
            self.setMinimumSize((ncols)*hwidth+dwidth,
                                (nrows)*dheight+hheight)
            self.setFixedSize((ncols)*hwidth+dwidth,
                              (nrows)*dheight+hheight)

    def clear(self):
        """Reset layout"""
        self._reset_layout()
        self.semi_states_dataset = {}
        self.semi_states_filter = {}

    def dragEnterEvent(self, event):
        print("drag enter event on data matrix")
        event.ignore()

    def dropEvent(self, event):
        print("drag drop event on data matrix")
        event.ignore()

    def fill_elements(self):
        for ii in range(self.num_datasets):
            for jj in range(self.num_filters):
                if self.glo.itemAtPosition(ii+1, jj+1) is None:
                    me = MatrixElement()
                    me.quickview_selected.connect(self.update_quickview)
                    self.glo.addWidget(me, ii+1, jj+1)

    def get_dataset_paths(self):
        """Return dataset paths in the order they are shown"""
        nrows = self.glo.rowCount()
        paths = []
        for ii in range(1, nrows):
            item = self.glo.itemAtPosition(ii, 0)
            paths.append(item.widget().path)
        return paths

    def get_matrix_element(self, dataset_id, filter_id):
        """Return matrix element matching dataset and filter identifiers"""
        ncols = self.glo.columnCount()
        nrows = self.glo.rowCount()
        for ii in range(1, nrows):
            ds = self.glo.itemAtPosition(ii, 0).widget()
            if ds.identifier == dataset_id:
                for jj in range(1, ncols):
                    f = self.glo.itemAtPosition(0, jj).widget()
                    if f.identifier == filter_id:
                        break
                break
        return self.glo.itemAtPosition(ii, jj).widget()

    @QtCore.pyqtSlot(str)
    def on_option_dataset(self, option):
        """Dataset option logic (remove, insert_anew, duplicate)"""
        sender = self.sender()
        idx = self.glo.indexOf(sender)
        row, _, _, _ = self.glo.getItemPosition(idx)
        state = self.__getstate__()
        ds_state = sender.__getstate__()
        if option == "insert_anew":
            ds_new = self.add_dataset(path=None)
            ds_state["identifier"] = ds_new.identifier
            state["datasets"].insert(row, ds_state)
        elif option == "duplicate":
            ds_new = self.add_dataset(path=None)
            # also set element states
            state["elements"][ds_new.identifier] = \
                state["elements"][ds_state["identifier"]]
            ds_state["identifier"] = ds_new.identifier
            state["datasets"].insert(row, ds_state)
        else:  # remove
            state["datasets"].pop(row-1)
            state["elements"].pop(ds_state["identifier"])
        self.__setstate__(state)

    @QtCore.pyqtSlot()
    def toggle_dataset_active(self):
        """Switch between all active, all inactive, previous state

        Modifies the matrix elements for a dataset/row,
        which is defined by the signal sender :class:`MatrixDataset`.
        Cyclic toggling order: semi -> all -> none
        """
        self.semi_states_filter = {}
        sender = self.sender()
        sid = sender.identifier
        state = self.__getstate__()["elements"][sid]
        num_actives = sum([s["active"] for s in state.values()])

        # update state according to the scheme in the docstring
        if num_actives == 0:
            if sid in self.semi_states_dataset:
                # use semi state
                oldstate = self.semi_states_dataset[sid]
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
            self.semi_states_dataset[sid] = copy.deepcopy(state)
            # toggle all to active
            for key in state:
                state[key]["active"] = True

        for fid in state:
            me = self.get_matrix_element(sid, fid)
            me.__setstate__(state[fid])

    @QtCore.pyqtSlot()
    def toggle_filter_active(self):
        """Switch between all active, all inactive, previous state

        Modifies the matrix elements for a filter/column,
        which is defined by the signal sender :class:`MatrixFilter`.
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
            if sid in self.semi_states_filter:
                # use semi state
                oldstate = self.semi_states_filter[sid]
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
            self.semi_states_filter[sid] = copy.deepcopy(state)
            # toggle all to active
            for key in state:
                state[key]["active"] = True

        for dsid in state:
            me = self.get_matrix_element(dsid, sid)
            me.__setstate__(state[dsid])

    def update_content(self):
        ncols = self.glo.columnCount()
        nrows = self.glo.rowCount()
        for ii in range(nrows):
            for jj in range(ncols):
                item = self.glo.itemAtPosition(ii, jj)
                if item is not None:
                    item.widget().update_content()

    @QtCore.pyqtSlot()
    def update_quickview(self):
        idx = self.glo.indexOf(self.sender())
        row, column, _, _ = self.glo.getItemPosition(idx)
        # decrement by header row/column
        row -= 1  # enumerates the dataset
        column -= 1  # enumerates the filter

        paths = self.get_dataset_paths()
        filters = []
        self.quickviewed.emit(paths[row], filters)
