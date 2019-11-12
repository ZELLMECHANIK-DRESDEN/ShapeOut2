import pkg_resources

from PyQt5 import uic, QtCore, QtWidgets

from ... import meta_tool
from ...pipeline import Dataslot


class MetaPanel(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.analysis", "ana_meta.ui")
        uic.loadUi(path_ui, self)

        self.comboBox_slots.currentIndexChanged.connect(self.update_content)
        self.update_content()

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

    def update_info_box(self, group_box, config, section):
        """Populate an individual group box with keyword-value pairs"""
        group_box.layout().setAlignment(QtCore.Qt.AlignTop)
        # cleanup
        for ii in reversed(range(group_box.layout().count())):
            item = group_box.layout().itemAt(ii).widget()
            if item is not None:
                item.deleteLater()
        # populate
        for key, value in config[section].items():
            widget = QtWidgets.QWidget()
            hbox = QtWidgets.QHBoxLayout()
            hbox.setAlignment(QtCore.Qt.AlignLeft)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.addWidget(QtWidgets.QLabel(key))
            hbox.addWidget(QtWidgets.QLabel("{}".format(value)))
            widget.setLayout(hbox)
            group_box.layout().addWidget(widget)

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
            cfg = meta_tool.get_rtdc_config(state["path"])
            self.update_info_box(self.groupBox_experiment, cfg,
                                 "experiment")
            self.update_info_box(self.groupBox_fluorescence, cfg,
                                 "fluorescence")
            self.update_info_box(self.groupBox_imaging, cfg,
                                 "imaging")
            self.update_info_box(self.groupBox_online_contour, cfg,
                                 "online_contour")
            self.update_info_box(self.groupBox_online_filter, cfg,
                                 "online_filter")
            self.update_info_box(self.groupBox_setup, cfg,
                                 "setup")
        else:
            self.setEnabled(False)
