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

        self.layout = QtWidgets.QGridLayout()
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.setAcceptDrops(True)

        # used for toggling between all active, all inactive and semi state
        self.semi_states_dataset = {}
        self.semi_states_filter = {}

    def __getstate__(self):
        """Logical states of the current data matrix"""
        # datasets
        nrows = self.layout.rowCount()
        datasets = []
        for ii in range(1, nrows):
            ds = self.layout.itemAtPosition(ii, 0).widget()
            datasets.append(ds.__getstate__())
        # filters
        ncols = self.layout.columnCount()
        filters = []
        for jj in range(1, ncols):
            f = self.layout.itemAtPosition(0, jj).widget()
            filters.append(f.__getstate__())
        # states
        mestates = {}
        for si in range(1, nrows):
            idds = self.layout.itemAtPosition(si, 0).widget().identifier
            idict = {}
            for sj in range(1, ncols):
                idf = self.layout.itemAtPosition(0, sj).widget().identifier
                me = self.layout.itemAtPosition(si, sj).widget()
                idict[idf] = me.__getstate__()
            mestates[idds] = idict
        state = {"elements": mestates,
                 "datasets": datasets,
                 "filters": filters}
        return state

    def __setstate__(self, state):
        raise NotImplementedError("TODO")

    def add_dataset(self, path, row=None):
        nrows = self.layout.rowCount()
        if nrows == 1:
            self.add_filter()

        if row is None:
            md = MatrixDataset(path)
            self.layout.addWidget(md, nrows, 0)
        else:
            # TODO: insert dataset at row
            assert False

        md.active_toggled.connect(self.toggle_dataset_active)

        self.fill_elements()
        self.adjust_size()

    def add_filter(self, evt=None):
        ncols = self.layout.columnCount()
        name = "FS{}".format(ncols)
        f = MatrixFilter(name)
        f.active_toggled.connect(self.toggle_filter_active)
        self.layout.addWidget(f, 0, ncols)
        self.fill_elements()
        self.adjust_size()

    def adjust_size(self):
        ncols = self.layout.columnCount()
        nrows = self.layout.rowCount()
        if ncols > 1 and nrows > 1:
            hwidth = self.layout.itemAtPosition(0, 1).geometry().width() + 2
            hheight = self.layout.itemAtPosition(0, 1).geometry().height() + 2
            dwidth = self.layout.itemAtPosition(1, 0).geometry().width() + 2
            dheight = self.layout.itemAtPosition(1, 0).geometry().height() + 2

            self.setMinimumSize((ncols-1)*hwidth+dwidth,
                                (nrows-1)*dheight+hheight)

    def clear(self):
        # TODO
        raise NotImplementedError("Clear not implemented")

    def dragEnterEvent(self, event):
        print("drag enter event on data matrix")
        event.ignore()

    def dropEvent(self, event):
        print("drag drop event on data matrix")
        event.ignore()

    def fill_elements(self):
        ncols = self.layout.columnCount()
        nrows = self.layout.rowCount()
        for ii in range(1, nrows):
            for jj in range(1, ncols):
                if self.layout.itemAtPosition(ii, jj) is None:
                    me = MatrixElement()
                    me.quickview_selected.connect(self.update_quickview)
                    self.layout.addWidget(me, ii, jj)

    def get_dataset_paths(self):
        """Return dataset paths in the order they are shown"""
        nrows = self.layout.rowCount()
        paths = []
        for ii in range(1, nrows):
            item = self.layout.itemAtPosition(ii, 0)
            paths.append(item.widget().path)
        return paths

    def get_matrix_element(self, dataset_id, filter_id):
        """Return matrix element matching dataset and filter identifiers"""
        ncols = self.layout.columnCount()
        nrows = self.layout.rowCount()
        for ii in range(1, nrows):
            ds = self.layout.itemAtPosition(ii, 0).widget()
            if ds.identifier == dataset_id:
                for jj in range(1, ncols):
                    f = self.layout.itemAtPosition(0, jj).widget()
                    if f.identifier == filter_id:
                        break
                break
        return self.layout.itemAtPosition(ii, jj).widget()

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
        ncols = self.layout.columnCount()
        nrows = self.layout.rowCount()
        for ii in range(nrows):
            for jj in range(ncols):
                item = self.layout.itemAtPosition(ii, jj)
                if isinstance(item, MatrixElement):
                    item.update_content()

    @QtCore.pyqtSlot()
    def update_quickview(self):
        idx = self.layout.indexOf(self.sender())
        row, column, _, _ = self.layout.getItemPosition(idx)
        # decrement by header row/column
        row -= 1  # enumerates the dataset
        column -= 1  # enumerates the filter

        paths = self.get_dataset_paths()
        filters = []
        self.quickviewed.emit(paths[row], filters)
