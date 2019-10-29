import pkg_resources

from PyQt5 import uic, QtCore, QtWidgets

from ... import meta_tool
from ...pipeline import Dataslot


class SlotPanel(QtWidgets.QWidget):
    #: Emitted when a shapeout2.pipeline.Dataslot is modified
    slots_changed = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.analysis", "ana_slot.ui")
        uic.loadUi(path_ui, self)
        self.pushButton_apply.clicked.connect(self.write_slot)
        self.pushButton_reset.clicked.connect(self.update_content)
        self.comboBox_slots.currentIndexChanged.connect(self.update_content)
        self.update_content()
        # current Shape-Out 2 pipeline
        self._pipeline = None

    def __getstate__(self):
        slot = self.current_slot
        state = {
            "name": self.lineEdit_name.text(),
            "path": slot.path,
            "color": self.lineEdit_color.text(),
            "fl names": {"fl1": self.lineEdit_fl1.text(),
                         "fl2": self.lineEdit_fl2.text(),
                         "fl3": self.lineEdit_fl3.text(),
                         }
        }
        return state

    def __setstate__(self, state):
        self.lineEdit_name.setText(state["name"])
        self.lineEdit_path.setText(str(state["path"]))
        self.lineEdit_color.setText(state["color"])
        self.lineEdit_fl1.setText(state["fl names"]["fl1"])
        self.lineEdit_fl2.setText(state["fl names"]["fl2"])
        self.lineEdit_fl3.setText(state["fl names"]["fl3"])

        features = meta_tool.get_rtdc_features(state["path"])

        hasfl1 = "fl1_max" in features
        self.lineEdit_fl1.setVisible(hasfl1)
        self.label_fl1.setVisible(hasfl1)

        hasfl2 = "fl2_max" in features
        self.lineEdit_fl2.setVisible(hasfl2)
        self.label_fl2.setVisible(hasfl2)

        hasfl3 = "fl3_max" in features
        self.lineEdit_fl3.setVisible(hasfl3)
        self.label_fl3.setVisible(hasfl3)

    @property
    def current_slot(self):
        if self.slot_ids:
            slot_index = self.comboBox_slots.currentIndex()
            slot_id = self.slot_ids[slot_index]
            slot = Dataslot.get_instances()[slot_id]
        else:
            slot = None
        return slot

    @property
    def slot_ids(self):
        """List of slot identifiers"""
        return sorted(Dataslot.get_instances().keys())

    @property
    def slot_names(self):
        """List of slot names"""
        return [Dataslot._instances[f].name for f in self.slot_ids]

    @property
    def pipeline(self):
        return self._pipeline

    def set_pipeline(self, pipeline):
        self._pipeline = pipeline

    def show_slot(self, slot_id):
        self.update_content(slot_index=self.slot_ids.index(slot_id))

    def update_content(self, event=None, slot_index=None):
        if self.slot_ids:
            self.setEnabled(True)
            # update combobox
            self.comboBox_slots.blockSignals(True)
            if slot_index is None:
                slot_index = self.comboBox_slots.currentIndex()
                if slot_index > len(self.slot_ids) - 1 or slot_index < 0:
                    slot_index = len(self.slot_ids) - 1
            self.comboBox_slots.clear()
            self.comboBox_slots.addItems(self.slot_names)
            self.comboBox_slots.setCurrentIndex(slot_index)
            self.comboBox_slots.blockSignals(False)
            # populate content
            slot = Dataslot.get_slot(identifier=self.slot_ids[slot_index])
            state = slot.__getstate__()
            self.__setstate__(state)
        else:
            self.setEnabled(False)

    def write_slot(self):
        """Update the shapeout2.pipeline.Dataslot instance"""
        # get current index
        slot_index = self.comboBox_slots.currentIndex()
        slot = Dataslot.get_slot(identifier=self.slot_names[slot_index])
        state = self.__getstate__()
        slot.__setstate__(state)
        self.slots_changed.emit()
        self.update_content()  # update slot combobox and visible fl names
