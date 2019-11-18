import copy

import numpy as np
from PyQt5 import QtCore, QtWidgets

from ... import pipeline

from .dm_dataset import MatrixDataset
from .dm_filter import MatrixFilter
from .dm_element import MatrixElement


class DataMatrix(QtWidgets.QWidget):
    quickviewed = QtCore.pyqtSignal(int, int)
    matrix_changed = QtCore.pyqtSignal()
    filter_modify_clicked = QtCore.pyqtSignal(str)
    slot_modify_clicked = QtCore.pyqtSignal(str)

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
        # slots
        datasets = []
        for ds in self.dataset_widgets:
            datasets.append(ds.__getstate__())
        # filters
        filters = []
        for fs in self.filters:
            filters.append(fs.__getstate__())
        # elements
        mestates = {}
        for ds in self.dataset_widgets:
            idict = {}
            for fs in self.filters:
                me = self.get_matrix_element(ds.identifier, fs.identifier)
                idict[fs.identifier] = me.__getstate__()
            mestates[ds.identifier] = idict
        state = {"elements": mestates,
                 "filters": filters,
                 "slots": datasets,
                 }
        return state

    def __setstate__(self, state):
        self.blockSignals(True)
        self.setUpdatesEnabled(False)
        self.clear()
        # dataset states
        for ii in range(len(state["slots"])):
            self.add_dataset(state=state["slots"][ii])
        # filter states
        for jj in range(len(state["filters"])):
            self.add_filter(state=state["filters"][jj])
        # make sure elements exist
        self.fill_elements()
        # element states
        MatrixElement._quick_view_instance = None
        for slot_id in state["elements"]:
            ds_state = state["elements"][slot_id]
            for filt_id in ds_state:
                me_state = ds_state[filt_id]
                me = self.get_matrix_element(slot_id, filt_id)
                me.__setstate__(me_state)
        self.adjust_size()
        self.blockSignals(False)
        self.setUpdatesEnabled(True)

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
        # add dummy corner element
        cl = QtWidgets.QLabel("Block\nMatrix")
        cl.setAlignment(QtCore.Qt.AlignCenter)
        cl.setMinimumSize(67, self.header_height)
        self.glo.addWidget(cl, 0, 0)
        self.setLayout(self.glo)
        self.adjust_size()

    @property
    def dataset_widgets(self):
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
            width = 67
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
            height = 99
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
    def header_height(self):
        """Data matrix horizontal header height"""
        for jj in range(1, self.glo.columnCount()):
            item = self.glo.itemAtPosition(0, jj)
            if item is not None:
                height = item.geometry().height()
                break
        else:
            height = 99
        return height

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

    def add_dataset(self, slot_id=None, state=None):
        """Add a dataset to the DataMatrix"""
        self.setUpdatesEnabled(False)
        md = MatrixDataset(identifier=slot_id, state=state)
        self.glo.addWidget(md, self.num_datasets+1, 0)
        md.active_toggled.connect(self.toggle_dataset_active)
        md.enabled_toggled.connect(self.toggle_dataset_enable)
        md.enabled_toggled.connect(self.plot_matrix.toggle_dataset_enable)
        md.option_action.connect(self.on_option_dataset)
        md.modify_clicked.connect(self.slot_modify_clicked.emit)
        self.fill_elements()
        self.adjust_size()
        self.plot_matrix.fill_elements()
        self.plot_matrix.adjust_size()
        self.setUpdatesEnabled(True)
        self.publish_matrix()
        return md

    def copy_dataset(self, slot_id, duplicate=True):
        """Insert a copy of a dataset in the DataMatrix"""
        state = self.__getstate__()

        # this state will be used for the new slot
        new_state, index = self.get_slot_state(slot_id, ret_index=True)
        # create a new slot
        slot = pipeline.Dataslot(path=new_state["path"])
        new_id = slot.identifier
        new_state["identifier"] = new_id
        if duplicate:
            # also set element states
            state["elements"][new_id] = state["elements"][slot_id]
            state["slots"].insert(index+1, new_state)
        else:
            # enable by default
            new_state["enabled"] = True
            state["slots"].insert(index+1, new_state)
        self.__setstate__(state)

    def rem_dataset(self, slot_id, not_exist_ok=False):
        """Remove a dataset from the DataMatrix"""
        state = self.__getstate__()
        pstate = self.plot_matrix.__getstate__()
        for slot_index, slot_state in enumerate(state["slots"]):
            if slot_state["identifier"] == slot_id:
                break
        else:
            if not_exist_ok:
                return
            else:
                raise ValueError("Slot '{}' does not exist!".format(slot_id))
        state["slots"].pop(slot_index)
        state["elements"].pop(slot_state["identifier"])
        pstate["elements"].pop(slot_state["identifier"])
        self.__setstate__(state)
        self.plot_matrix.__setstate__(pstate)

    def add_filter(self, identifier=None, state=None):
        self.setUpdatesEnabled(False)
        mf = MatrixFilter(identifier=identifier, state=state)
        mf.active_toggled.connect(self.toggle_filter_active)
        mf.enabled_toggled.connect(self.toggle_filter_enable)
        mf.option_action.connect(self.on_option_filter)
        mf.modify_clicked.connect(self.filter_modify_clicked.emit)
        self.glo.addWidget(mf, 0, self.num_filters+1)
        self.fill_elements()
        self.adjust_size()
        self.setUpdatesEnabled(True)
        self.publish_matrix()
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

    def changed_element(self):
        self.publish_matrix()

    def changed_quickview(self):
        slot_index_qv, filt_index_qv = self.get_quickview_indices()
        if slot_index_qv is not None and filt_index_qv is not None:
            self.quickviewed.emit(slot_index_qv, filt_index_qv)

    def enable_quickview(self, b=True):
        if b:
            MatrixElement._quick_view_instance = self._old_quickview_instance
        else:
            self._old_quickview_instance = MatrixElement._quick_view_instance
            MatrixElement._quick_view_instance = None
        self.update_content()

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
        for slot_sate in state["slots"]:
            for filt_state in state["filters"]:
                if not slot_sate["enabled"] or not filt_state["enabled"]:
                    me = self.get_matrix_element(slot_sate["identifier"],
                                                 filt_state["identifier"])
                    mstate = me.__getstate__()
                    mstate["enabled"] = False
                    me.__setstate__(mstate)

    def get_slot_state(self, slot_id, ret_index=False):
        for ii, ds in enumerate(self.dataset_widgets):
            if ds.identifier == slot_id:
                break
        else:
            raise KeyError("Dataset '{}' not found!".format(slot_id))
        if ret_index:
            return ds.__getstate__(), ii
        else:
            return ds.__getstate__()

    def get_filter_state(self, filter_id):
        for fs in self.filters:
            if fs.identifier == filter_id:
                break
        else:
            raise KeyError("Filter '{}' not found!".format(filter_id))
        return fs.__getstate__()

    def get_matrix_element(self, slot_id, filt_id):
        """Return matrix element matching dataset and filter identifiers"""
        ii, jj = self.get_matrix_indices(slot_id, filt_id)
        return self.glo.itemAtPosition(ii, jj).widget()

    def get_matrix_indices(self, slot_id, filt_id):
        ncols = self.glo.columnCount()
        nrows = self.glo.rowCount()
        for ii in range(1, nrows):
            ds = self.glo.itemAtPosition(ii, 0).widget()
            if ds.identifier == slot_id:
                for jj in range(1, ncols):
                    f = self.glo.itemAtPosition(0, jj).widget()
                    if f.identifier == filt_id:
                        break
                else:
                    raise KeyError("Filter '{}' not found!".format(filt_id))
                break
        else:
            raise KeyError("Dataset '{}' not found!".format(slot_id))
        return ii, jj

    def get_quickview_ids(self):
        current = MatrixElement._quick_view_instance
        if current is not None:
            state = self.__getstate__()
            for slot_id in state["elements"]:
                ds_state = state["elements"][slot_id]
                for filt_id in ds_state:
                    me = self.get_matrix_element(slot_id, filt_id)
                    if current == me:
                        return slot_id, filt_id
        else:
            return None, None

    def get_quickview_indices(self):
        slot_id, filt_id = self.get_quickview_ids()
        if slot_id is not None:
            ii, jj = self.get_matrix_indices(slot_id, filt_id)
            return ii - 1, jj - 1
        else:
            return None, None

    @QtCore.pyqtSlot(str)
    def on_option_dataset(self, option):
        """Dataset option logic (remove, insert_anew, duplicate)"""
        sender = self.sender()
        ds_state = sender.__getstate__()
        slot_id = ds_state["identifier"]
        # remember current quickview element ids
        qvslot_id, qv_filt_id = self.get_quickview_ids()
        if option == "insert_anew":
            self.copy_dataset(slot_id=slot_id, duplicate=False)
        elif option == "duplicate":
            self.copy_dataset(slot_id=slot_id, duplicate=True)
        else:  # remove
            self.rem_dataset(slot_id=slot_id)
        # re-apply current quickview ids
        try:
            meqv = self.get_matrix_element(qvslot_id, qv_filt_id)
        except KeyError:
            pass
        else:
            MatrixElement._quick_view_instance = meqv
            self.update_content()
        self.publish_matrix()

    @QtCore.pyqtSlot(str)
    def on_option_filter(self, option):
        """Filter option logic (remove, duplicate)"""
        sender = self.sender()
        idx = self.glo.indexOf(sender)
        _, column, _, _ = self.glo.getItemPosition(idx)
        state = self.__getstate__()
        f_state = sender.__getstate__()
        # remember current quickview element ids
        qvslot_id, qv_filt_id = self.get_quickview_ids()
        if option == "duplicate":
            filt = pipeline.Filter()
            f_state["identifier"] = filt.identifier
            f_state["name"] = filt.name
            state["filters"].insert(column, f_state)
        else:  # remove
            state["filters"].pop(column-1)
            for ds_key in state["elements"]:
                state["elements"][ds_key].pop(f_state["identifier"])
        self.__setstate__(state)
        # re-apply current quickview ids
        try:
            meqv = self.get_matrix_element(qvslot_id, qv_filt_id)
        except KeyError:
            pass
        else:
            MatrixElement._quick_view_instance = meqv
            self.update_content()
        self.publish_matrix()

    def publish_matrix(self):
        """Publish state via self.matrix_changed signal for Pipeline"""
        if not self.signalsBlocked():
            self.matrix_changed.emit()
            self.changed_quickview()

    @QtCore.pyqtSlot()
    def toggle_dataset_active(self):
        """Switch between all active, all inactive, previous state

        Modifies the matrix elements for a dataset/row,
        which is defined by the signal sender :class:`MatrixDataset`.
        Cyclic toggling order: semi -> all -> none
        """
        self.semi_states_filter = {}
        sender = self.sender()
        slot_id = sender.identifier
        state = self.get_slot_state(slot_id)
        num_actives = sum([s["active"] for s in state.values()])

        # update state according to the scheme in the docstring
        if num_actives == 0:
            if slot_id in self.semi_states_dataset:
                # use semi state
                oldstate = self.semi_states_dataset[slot_id]
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
            self.semi_states_dataset[slot_id] = copy.deepcopy(state)
            # toggle all to active
            for key in state:
                state[key]["active"] = True

        for filt_id in state:
            me = self.get_matrix_element(slot_id, filt_id)
            me.__setstate__(state[filt_id])
        self.publish_matrix()

    @QtCore.pyqtSlot(bool)
    def toggle_dataset_enable(self, enabled):
        sender = self.sender()
        slot_id = sender.identifier
        state = self.__getstate__()
        for filt_id in state["elements"][slot_id]:
            # make sure that disabled filters are honored
            fstate = self.get_filter_state(filt_id)
            fenabled = fstate["enabled"]
            # update element widget
            me = self.get_matrix_element(slot_id, filt_id)
            mstate = me.__getstate__()
            mstate["enabled"] = np.logical_and(enabled, fenabled)
            me.__setstate__(mstate)
        self.publish_matrix()

    @QtCore.pyqtSlot()
    def toggle_filter_active(self):
        """Switch between all active, all inactive, previous state

        Modifies the matrix elements for a filter/column,
        which is defined by the signal sender :class:`MatrixFilter`.
        Cyclic toggling order: semi -> all -> none
        """
        self.semi_states_dataset = {}
        sender = self.sender()
        filt_id = sender.identifier

        states = self.__getstate__()["elements"]
        state = {}
        for key in states:
            state[key] = states[key][filt_id]

        num_actives = sum([s["active"] for s in state.values()])

        # update state according to the scheme in the docstring
        if num_actives == 0:
            if filt_id in self.semi_states_filter:
                # use semi state
                oldstate = self.semi_states_filter[filt_id]
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
            self.semi_states_filter[filt_id] = copy.deepcopy(state)
            # toggle all to active
            for key in state:
                state[key]["active"] = True

        for slot_id in state:
            me = self.get_matrix_element(slot_id, filt_id)
            me.__setstate__(state[slot_id])
        self.publish_matrix()

    @QtCore.pyqtSlot(bool)
    def toggle_filter_enable(self, enabled):
        sender = self.sender()
        sid = sender.identifier
        state = self.__getstate__()
        for slot_id in state["elements"]:
            # make sure that disabled filters are honored
            dstate = self.get_slot_state(slot_id)
            denabled = dstate["enabled"]
            # update element widget
            me = self.get_matrix_element(slot_id, sid)
            mstate = me.__getstate__()
            mstate["enabled"] = np.logical_and(enabled, denabled)
            me.__setstate__(mstate)
        self.publish_matrix()

    def update_content(self):
        ncols = self.glo.columnCount()
        nrows = self.glo.rowCount()
        for ii in range(nrows):
            for jj in range(ncols):
                if ii == 0 and jj == 0:
                    # block matrix label
                    continue
                item = self.glo.itemAtPosition(ii, jj)
                if item is not None:
                    item.widget().update_content()
