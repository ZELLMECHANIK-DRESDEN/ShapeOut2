import copy

import numpy as np
from PyQt5 import QtCore, QtWidgets

from .dm_dataset import MatrixDataset
from .dm_filter import MatrixFilter
from .dm_element import MatrixElement


class DataMatrix(QtWidgets.QWidget):
    quickviewed = QtCore.pyqtSignal(int, int)
    matrix_changed = QtCore.pyqtSignal(int, int)

    def __init__(self, parent=None):
        super(DataMatrix, self).__init__(parent)

        self.glo = None
        self._reset_layout()

        self.setAcceptDrops(True)

        # used for toggling between all active, all inactive and semi state
        self.semi_states_dataset = {}
        self.semi_states_filter = {}

        # used for remembering quickview element
        self._old_quickview_instance = None

    def __getstate__(self):
        """Logical states of the current data matrix"""
        # datasets
        datasets = []
        for ds in self.datasets:
            datasets.append(ds.__getstate__())
        # filters
        filters = []
        for fs in self.filters:
            filters.append(fs.__getstate__())
        # elements
        mestates = {}
        for ds in self.datasets:
            idict = {}
            for fs in self.filters:
                me = self.get_matrix_element(ds.identifier, fs.identifier)
                idict[fs.identifier] = me.__getstate__()
            mestates[ds.identifier] = idict
        state = {"elements": mestates,
                 "datasets": datasets,
                 "filters": filters}
        return state

    def __setstate__(self, state):
        self.clear()
        # dataset states
        for ii in range(len(state["datasets"])):
            self.add_dataset(state=state["datasets"][ii])
        # filter states
        for jj in range(len(state["filters"])):
            self.add_filter(state=state["filters"][jj])
        # make sure elements exist
        self.fill_elements()
        # element states
        MatrixElement._quick_view_instance = None
        for ds_key in state["elements"]:
            ds_state = state["elements"][ds_key]
            for f_key in ds_state:
                me_state = ds_state[f_key]
                me = self.get_matrix_element(ds_key, f_key)
                me.__setstate__(me_state)

        self.adjust_size()

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
    def datasets(self):
        datasets = []
        for ii in range(self.glo.rowCount()):
            item = self.glo.itemAtPosition(ii+1, 0)
            if item is not None:
                ds = item.widget()
                datasets.append(ds)
        return datasets

    @property
    def element_width(self):
        """Data matrix element width (without 2px spacing)"""
        for jj in range(1, self.glo.columnCount()-1):
            item = self.glo.itemAtPosition(0, jj)
            if item is not None:
                width = item.geometry().width()
                break
        else:
            width = 90
        return width

    @property
    def element_height(self):
        """Data matrix element height (without 2px spacing)"""
        for ii in range(1, self.glo.rowCount()-1):
            item = self.glo.itemAtPosition(ii, 0)
            if item is not None:
                height = item.geometry().height()
                break
        else:
            height = 90
        return height

    @property
    def filters(self):
        filters = []
        for jj in range(self.glo.columnCount()):
            item = self.glo.itemAtPosition(0, jj+1)
            if item is not None:
                fs = item.widget()
                filters.append(fs)
        return filters

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

    @property
    def plot_matrix(self):
        for ch in self.parent().children():
            if ch.__class__.__name__ == "PlotMatrix":
                break
        else:
            raise KeyError("PlotMatrix not found!")
        return ch

    def add_dataset(self, path=None, identifier=None, state=None):
        md = MatrixDataset(path=path, identifier=identifier, state=state)
        self.glo.addWidget(md, self.num_datasets+1, 0)
        md.active_toggled.connect(self.toggle_dataset_active)
        md.enabled_toggled.connect(self.toggle_dataset_enable)
        md.enabled_toggled.connect(self.plot_matrix.toggle_dataset_enable)
        md.option_action.connect(self.on_option_dataset)
        self.fill_elements()
        self.adjust_size()
        self.plot_matrix.fill_elements()
        self.plot_matrix.adjust_size()
        return md

    def add_filter(self, name=None, identifier=None, state=None):
        mf = MatrixFilter(name=name, identifier=identifier, state=state)
        mf.active_toggled.connect(self.toggle_filter_active)
        mf.enabled_toggled.connect(self.toggle_filter_enable)
        mf.option_action.connect(self.on_option_filter)
        self.glo.addWidget(mf, 0, self.num_filters+1)
        self.fill_elements()
        self.adjust_size()
        return mf

    def adjust_size(self):
        QtWidgets.QApplication.processEvents()
        ncols = self.num_filters
        nrows = self.num_datasets
        if ncols and nrows:
            hwidth = self.element_width + 2
            hheight = self.glo.itemAtPosition(0, 1).geometry().height()
            dwidth = self.glo.itemAtPosition(1, 0).geometry().width()
            dheight = self.element_height + 2
            self.setMinimumSize(ncols*hwidth+dwidth,
                                nrows*dheight+hheight)
            self.setFixedSize(ncols*hwidth+dwidth,
                              nrows*dheight+hheight)

    @QtCore.pyqtSlot()
    def changed_element(self):
        idx = self.glo.indexOf(self.sender())
        row, column, _, _ = self.glo.getItemPosition(idx)
        # decrement by header row/column
        slot_index = row - 1  # enumerates the dataset
        filt_index = column - 1  # enumerates the filter
        slot_index_qv, filt_index_qv = self.get_quickview_indices()
        self.matrix_changed.emit(slot_index, filt_index)
        if slot_index_qv == slot_index and filt_index_qv >= filt_index:
            self.quickviewed.emit(slot_index_qv, filt_index_qv)

    @QtCore.pyqtSlot()
    def changed_quickview(self):
        slot_index_qv, filt_index_qv = self.get_quickview_indices()
        self.quickviewed.emit(slot_index_qv, filt_index_qv)

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

    def enable_quickview(self, b=True):
        if b:
            MatrixElement._quick_view_instance = self._old_quickview_instance
        else:
            self._old_quickview_instance = MatrixElement._quick_view_instance
            MatrixElement._quick_view_instance = None
        self.update_content()

    def fill_elements(self):
        # add widgets
        for ii in range(self.num_datasets):
            for jj in range(self.num_filters):
                if self.glo.itemAtPosition(ii+1, jj+1) is None:
                    me = MatrixElement()
                    me.quickview_selected.connect(self.changed_quickview)
                    me.element_changed.connect(self.changed_element)
                    self.glo.addWidget(me, ii+1, jj+1)
        # make sure enabled/disabled is honored
        state = self.__getstate__()
        for ds in state["datasets"]:
            for f in state["filters"]:
                if not ds["enabled"] or not f["enabled"]:
                    me = self.get_matrix_element(ds["identifier"],
                                                 f["identifier"])
                    mstate = me.__getstate__()
                    mstate["enabled"] = False
                    me.__setstate__(mstate)

    def get_dataset(self, dataset_id):
        for ds in self.datasets:
            if ds.identifier == dataset_id:
                break
        else:
            raise KeyError("Dataset '{}' not found!".format(dataset_id))
        return ds

    def get_dataset_paths(self):
        """Return dataset paths in the order they are shown"""
        paths = []
        for ds in self.datasets:
            paths.append(ds.path)
        return paths

    def get_filter(self, filter_id):
        for fs in self.filters:
            if fs.identifier == filter_id:
                break
        else:
            raise KeyError("Filter '{}' not found!".format(filter_id))
        return fs

    def get_matrix_element(self, dataset_id, filter_id):
        """Return matrix element matching dataset and filter identifiers"""
        ii, jj = self.get_matrix_indices(dataset_id, filter_id)
        return self.glo.itemAtPosition(ii, jj).widget()

    def get_matrix_indices(self, dataset_id, filter_id):
        ncols = self.glo.columnCount()
        nrows = self.glo.rowCount()
        for ii in range(1, nrows):
            ds = self.glo.itemAtPosition(ii, 0).widget()
            if ds.identifier == dataset_id:
                for jj in range(1, ncols):
                    f = self.glo.itemAtPosition(0, jj).widget()
                    if f.identifier == filter_id:
                        break
                else:
                    raise KeyError("Filter '{}' not found!".format(filter_id))
                break
        else:
            raise KeyError("Dataset '{}' not found!".format(dataset_id))
        return ii, jj

    def get_quickview_ids(self):
        current = MatrixElement._quick_view_instance
        if current is not None:
            state = self.__getstate__()
            for ds_key in state["elements"]:
                ds_state = state["elements"][ds_key]
                for f_key in ds_state:
                    me = self.get_matrix_element(ds_key, f_key)
                    if current == me:
                        return ds_key, f_key
        else:
            return None, None

    def get_quickview_indices(self):
        ds_key, f_key = self.get_quickview_ids()
        if ds_key is not None:
            ii, jj = self.get_matrix_indices(ds_key, f_key)
            return ii - 1, jj - 1
        else:
            return None, None

    @QtCore.pyqtSlot(str)
    def on_option_dataset(self, option):
        """Dataset option logic (remove, insert_anew, duplicate)"""
        sender = self.sender()
        idx = self.glo.indexOf(sender)
        row, _, _, _ = self.glo.getItemPosition(idx)
        state = self.__getstate__()
        ds_state = sender.__getstate__()
        pstate = self.plot_matrix.__getstate__()
        # remember current quickview element ids
        qv_ds, qv_f = self.get_quickview_ids()
        if option == "insert_anew":
            ds_new = self.add_dataset(path=ds_state["path"])
            ds_state["identifier"] = ds_new.identifier
            # enable by default
            ds_state["enabled"] = True
            state["datasets"].insert(row, ds_state)
        elif option == "duplicate":
            ds_new = self.add_dataset(path=ds_state["path"])
            # also set element states
            state["elements"][ds_new.identifier] = \
                state["elements"][ds_state["identifier"]]
            ds_state["identifier"] = ds_new.identifier
            state["datasets"].insert(row, ds_state)
        else:  # remove
            state["datasets"].pop(row-1)
            state["elements"].pop(ds_state["identifier"])
            pstate["elements"].pop(ds_state["identifier"])
        self.__setstate__(state)
        self.plot_matrix.__setstate__(pstate)
        # re-apply current quickview ids
        try:
            meqv = self.get_matrix_element(qv_ds, qv_f)
        except KeyError:
            pass
        else:
            MatrixElement._quick_view_instance = meqv
            self.update_content()

    @QtCore.pyqtSlot(str)
    def on_option_filter(self, option):
        """Filter option logic (remove, duplicate)"""
        sender = self.sender()
        idx = self.glo.indexOf(sender)
        _, column, _, _ = self.glo.getItemPosition(idx)
        state = self.__getstate__()
        f_state = sender.__getstate__()
        # remember current quickview element ids
        qv_ds, qv_f = self.get_quickview_ids()
        if option == "duplicate":
            f_new = self.add_filter()
            f_state["identifier"] = f_new.identifier
            f_state["name"] = f_new.name
            state["filters"].insert(column, f_state)
        else:  # remove
            state["filters"].pop(column-1)
            for ds_key in state["elements"]:
                state["elements"][ds_key].pop(f_state["identifier"])
        self.__setstate__(state)
        # re-apply current quickview ids
        try:
            meqv = self.get_matrix_element(qv_ds, qv_f)
        except KeyError:
            pass
        else:
            MatrixElement._quick_view_instance = meqv
            self.update_content()

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
        self.changed_quickview()

    @QtCore.pyqtSlot(bool)
    def toggle_dataset_enable(self, enabled):
        sender = self.sender()
        sid = sender.identifier
        state = self.__getstate__()
        for f_key in state["elements"][sid]:
            # make sure that disabled filters are honored
            fstate = self.get_filter(f_key).__getstate__()
            fenabled = fstate["enabled"]
            # update element widget
            me = self.get_matrix_element(sid, f_key)
            mstate = me.__getstate__()
            mstate["enabled"] = np.logical_and(enabled, fenabled)
            me.__setstate__(mstate)
        self.changed_quickview()

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
        self.changed_quickview()

    @QtCore.pyqtSlot(bool)
    def toggle_filter_enable(self, enabled):
        sender = self.sender()
        sid = sender.identifier
        state = self.__getstate__()
        for ds_key in state["elements"]:
            # make sure that disabled filters are honored
            dstate = self.get_dataset(ds_key).__getstate__()
            denabled = dstate["enabled"]
            # update element widget
            me = self.get_matrix_element(ds_key, sid)
            mstate = me.__getstate__()
            mstate["enabled"] = np.logical_and(enabled, denabled)
            me.__setstate__(mstate)
        self.changed_quickview()

    def update_content(self):
        ncols = self.glo.columnCount()
        nrows = self.glo.rowCount()
        for ii in range(nrows):
            for jj in range(ncols):
                item = self.glo.itemAtPosition(ii, jj)
                if item is not None:
                    item.widget().update_content()
