import copy
import pkg_resources
import warnings

import dclab
from dclab.rtdc_dataset.check import VALID_CHOICES
import numpy as np
from PyQt5 import uic, QtCore, QtWidgets

from ... import meta_tool
from ...pipeline import Dataslot


class SlotPanel(QtWidgets.QWidget):
    #: Emitted when a shapeout2.pipeline.Dataslot is to be changed
    slot_changed = QtCore.pyqtSignal(dict)
    #: Emitted when the pipeline is to be changed
    pipeline_changed = QtCore.pyqtSignal(dict)

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.analysis", "ana_slot.ui")
        uic.loadUi(path_ui, self)
        # current Shape-Out 2 pipeline
        self._pipeline = None
        # signals
        self.pushButton_anew.clicked.connect(self.on_anew_slot)
        self.pushButton_duplicate.clicked.connect(self.on_duplicate_slot)
        self.pushButton_remove.clicked.connect(self.on_remove_slot)
        self.pushButton_apply.clicked.connect(self.write_slot)
        self.pushButton_reset.clicked.connect(self.update_content)
        self.comboBox_slots.currentIndexChanged.connect(self.update_content)
        # init
        self._init_emodulus()
        self.update_content()

    def __getstate__(self):
        slot_state = self.current_slot_state
        if self.comboBox_temp.currentData() in ["manual", "config"]:
            emod_temp = self.doubleSpinBox_temp.value()
        else:
            emod_temp = np.nan
        if self.comboBox_medium.currentData() == "other":
            emod_visc = self.doubleSpinBox_visc.value()
        else:
            emod_visc = np.nan
        state = {
            "identifier": slot_state["identifier"],
            "name": self.lineEdit_name.text(),
            "path": slot_state["path"],
            "color": self.pushButton_color.color().name(),
            "slot used": self.checkBox_use.isChecked(),
            "fl names": {"FL-1": self.lineEdit_fl1.text(),
                         "FL-2": self.lineEdit_fl2.text(),
                         "FL-3": self.lineEdit_fl3.text(),
                         },
            "crosstalk": {
                "crosstalk fl12": self.doubleSpinBox_ct12.value(),
                "crosstalk fl13": self.doubleSpinBox_ct13.value(),
                "crosstalk fl21": self.doubleSpinBox_ct21.value(),
                "crosstalk fl23": self.doubleSpinBox_ct23.value(),
                "crosstalk fl31": self.doubleSpinBox_ct31.value(),
                "crosstalk fl32": self.doubleSpinBox_ct32.value(),
            },
            "emodulus": {
                "emodulus enabled": slot_state["emodulus"]["emodulus enabled"],
                "emodulus model": "elastic sphere",
                "emodulus medium": self.comboBox_medium.currentData(),
                "emodulus scenario": self.comboBox_temp.currentData(),
                "emodulus temperature": emod_temp,
                "emodulus viscosity": emod_visc,
            }
        }
        return state

    def __setstate__(self, state):
        cur_state = self.current_slot_state
        if cur_state["identifier"] != state["identifier"]:
            raise ValueError("Slot identifier mismatch!")
        self.lineEdit_name.setText(state["name"])
        self.lineEdit_path.setText(str(state["path"]))
        self.pushButton_color.setColor(state["color"])
        self.lineEdit_fl1.setText(state["fl names"]["FL-1"])
        self.lineEdit_fl2.setText(state["fl names"]["FL-2"])
        self.lineEdit_fl3.setText(state["fl names"]["FL-3"])
        self.checkBox_use.setChecked(state["slot used"])
        # crosstalk
        crosstalk = state["crosstalk"]
        self.doubleSpinBox_ct12.setValue(crosstalk["crosstalk fl12"])
        self.doubleSpinBox_ct13.setValue(crosstalk["crosstalk fl13"])
        self.doubleSpinBox_ct21.setValue(crosstalk["crosstalk fl21"])
        self.doubleSpinBox_ct23.setValue(crosstalk["crosstalk fl23"])
        self.doubleSpinBox_ct31.setValue(crosstalk["crosstalk fl31"])
        self.doubleSpinBox_ct32.setValue(crosstalk["crosstalk fl32"])
        # emodulus
        # this has to be done first, because self.comboBox_medium
        # triggers on_medium which triggers on_temperature
        self._init_emodulus_temp_choices()
        emodulus = state["emodulus"]
        self.groupBox_emod.setVisible(emodulus["emodulus enabled"])
        idx_med = self.comboBox_medium.findData(emodulus["emodulus medium"])
        self.comboBox_medium.setCurrentIndex(idx_med)
        # https://dclab.readthedocs.io/en/latest/sec_av_emodulus.html
        scenario = emodulus.get("emodulus scenario", "manual")
        idx_scen = self.comboBox_temp.findData(scenario)
        self.comboBox_temp.blockSignals(True)
        self.comboBox_temp.setCurrentIndex(idx_scen)
        self.comboBox_temp.blockSignals(False)
        # This has to be done after setting the scenario
        # (otherwise it might be overridden in the frontend)
        self.doubleSpinBox_temp.setValue(emodulus["emodulus temperature"])
        self.doubleSpinBox_visc.setValue(emodulus["emodulus viscosity"])

        # Fluorescence data visibility
        features = meta_tool.get_rtdc_features(state["path"])
        hasfl1 = "fl1_max" in features
        hasfl2 = "fl2_max" in features
        hasfl3 = "fl3_max" in features

        # labels
        self.lineEdit_fl1.setVisible(hasfl1)
        self.label_fl1.setVisible(hasfl1)
        self.lineEdit_fl2.setVisible(hasfl2)
        self.label_fl2.setVisible(hasfl2)
        self.lineEdit_fl3.setVisible(hasfl3)
        self.label_fl3.setVisible(hasfl3)

        # crosstalk matrix
        self.label_from_fl1.setVisible(hasfl1 & hasfl2 | hasfl1 & hasfl3)
        self.label_from_fl2.setVisible(hasfl2 & hasfl1 | hasfl2 & hasfl3)
        self.label_from_fl3.setVisible(hasfl3 & hasfl1 | hasfl3 & hasfl2)
        self.label_to_fl1.setVisible(hasfl1 & hasfl2 | hasfl1 & hasfl3)
        self.label_to_fl2.setVisible(hasfl2 & hasfl1 | hasfl2 & hasfl3)
        self.label_to_fl3.setVisible(hasfl3 & hasfl1 | hasfl3 & hasfl2)
        self.doubleSpinBox_ct12.setVisible(hasfl1 & hasfl2)
        self.doubleSpinBox_ct13.setVisible(hasfl1 & hasfl3)
        self.doubleSpinBox_ct21.setVisible(hasfl2 & hasfl1)
        self.doubleSpinBox_ct23.setVisible(hasfl2 & hasfl3)
        self.doubleSpinBox_ct31.setVisible(hasfl3 & hasfl1)
        self.doubleSpinBox_ct32.setVisible(hasfl3 & hasfl2)

        self.groupBox_fl_labels.setVisible(hasfl1 | hasfl2 | hasfl3)
        self.groupBox_fl_cross.setVisible(hasfl1 | hasfl2 | hasfl3)

    def _init_emodulus(self):
        self.comboBox_medium.clear()
        for choice in VALID_CHOICES["setup"]["medium"]:
            if choice == "CellCarrierB":
                name = "CellCarrier B"  # [sic]
            else:
                name = choice
            self.comboBox_medium.addItem(name, choice)
        self.comboBox_medium.addItem("not defined", "undefined")
        self.comboBox_medium.currentIndexChanged.connect(self.on_medium)
        self._init_emodulus_temp_choices()
        self.comboBox_temp.currentIndexChanged.connect(self.on_temperature)
        self.doubleSpinBox_temp.valueChanged.connect(self.on_temperature)

    def _init_emodulus_temp_choices(self):
        """populate the temperature comboBox with all available entries

        The previous selection is preserved. Signals are blocked.
        """
        self.comboBox_temp.blockSignals(True)
        cursel = self.comboBox_temp.currentData()
        self.comboBox_temp.clear()
        ds = self.get_dataset()
        if ds is not None:
            if "temp" in ds:
                self.comboBox_temp.addItem("From feature", "feature")
            if "temperature" in ds.config["setup"]:
                self.comboBox_temp.addItem("From meta data", "config")
        self.comboBox_temp.addItem("Manual", "manual")
        idx = self.comboBox_temp.findData(cursel)
        self.comboBox_temp.setCurrentIndex(idx)
        self.comboBox_temp.blockSignals(False)

    @property
    def current_slot_state(self):
        if self.slot_ids:
            slot_index = self.comboBox_slots.currentIndex()
            slot_state = self.pipeline.slots[slot_index].__getstate__()
        else:
            slot_state = None
        return slot_state

    @property
    def pipeline(self):
        return self._pipeline

    @property
    def slot_ids(self):
        """List of slot identifiers"""
        if self.pipeline is None:
            return []
        else:
            return [slot.identifier for slot in self.pipeline.slots]

    @property
    def slot_names(self):
        """List of slot names"""
        if self.pipeline is None:
            return []
        else:
            return [slot.name for slot in self.pipeline.slots]

    def get_dataset(self):
        """Return dataset associated with the current slot index

        Returns None if there is no dataset in the pipeline.
        """
        if self.pipeline is not None and self.pipeline.slots:
            slot_index = self.comboBox_slots.currentIndex()
            slot = self.pipeline.slots[slot_index]
            return slot.get_dataset()
        else:
            return None

    def on_anew_slot(self):
        slot_state = self.__getstate__()
        new_slot = Dataslot(slot_state["path"])
        pos = self.pipeline.slot_ids.index(slot_state["identifier"])
        self.pipeline.add_slot(new_slot, index=pos+1)
        state = self.pipeline.__getstate__()
        self.pipeline_changed.emit(state)

    def on_duplicate_slot(self):
        # determine the new filter state
        slot_state = self.__getstate__()
        new_state = copy.deepcopy(slot_state)
        new_slot = Dataslot(slot_state["path"])
        new_state["identifier"] = new_slot.identifier
        new_state["name"] = new_slot.name
        new_slot.__setstate__(new_state)
        # determine the filter position
        pos = self.pipeline.slot_ids.index(slot_state["identifier"])
        self.pipeline.add_slot(new_slot, index=pos+1)
        state = self.pipeline.__getstate__()
        self.pipeline_changed.emit(state)

    def on_remove_slot(self):
        slot_state = self.__getstate__()
        self.pipeline.remove_slot(slot_state["identifier"])
        state = self.pipeline.__getstate__()
        self.pipeline_changed.emit(state)

    def on_medium(self):
        """Called if the user chose a different medium"""
        medium = self.comboBox_medium.currentData()
        if medium == "undefined":
            self.doubleSpinBox_temp.setValue(np.nan)
            self.doubleSpinBox_temp.setEnabled(False)
            self.comboBox_temp.setEnabled(False)
            self.doubleSpinBox_visc.setEnabled(False)
            self.doubleSpinBox_visc.setStyleSheet("border-width: 2px")
        elif medium == "other":
            self.doubleSpinBox_temp.setValue(np.nan)
            self.doubleSpinBox_temp.setEnabled(False)
            self.comboBox_temp.setEnabled(False)
            self.doubleSpinBox_visc.setEnabled(True)
            self.doubleSpinBox_visc.setReadOnly(False)
            self.doubleSpinBox_visc.setStyleSheet("border-width: 2px")
        else:
            self.doubleSpinBox_temp.setEnabled(True)
            self.comboBox_temp.setEnabled(True)
            self.doubleSpinBox_visc.setEnabled(True)
            self.doubleSpinBox_visc.setReadOnly(True)
            self.on_temperature()

    def on_temperature(self):
        """Called on temperature selections (comboBox, doubleSpinBox)"""
        medium = self.comboBox_medium.currentData()
        tselec = self.comboBox_temp.currentData()
        if tselec in ["manual", "config"]:
            if tselec == "manual":
                temperature = self.doubleSpinBox_temp.value()
                self.doubleSpinBox_temp.setReadOnly(False)
                self.doubleSpinBox_temp.setEnabled(True)
            elif tselec == "config":
                # get temperature from dataset
                ds = self.get_dataset()
                temperature = ds.config["setup"]["temperature"]
                self.doubleSpinBox_temp.setReadOnly(True)
                self.doubleSpinBox_temp.setEnabled(True)
                self.doubleSpinBox_temp.setValue(temperature)
            elif tselec == "feature":
                temperature = np.nan
                self.doubleSpinBox_temp.setEnabled(False)
                self.doubleSpinBox_temp.setValue(temperature)
            # For user convenience, also show the viscosity
            if medium in dclab.features.emodulus.viscosity.KNOWN_MEDIA:
                # compute viscosity
                state = self.__getstate__()
                cfg = meta_tool.get_rtdc_config(state["path"])
                with warnings.catch_warnings(record=True) as w:
                    # Warn the user if the temperature is out-of-range
                    warnings.simplefilter("always")
                    visc = dclab.features.emodulus.viscosity.get_viscosity(
                        medium=medium,
                        channel_width=cfg["setup"]["channel width"],
                        flow_rate=cfg["setup"]["flow rate"],
                        temperature=temperature)
                    for wi in w:
                        if issubclass(wi.category,
                                      dclab.features.emodulus.viscosity.
                                      TemperatureOutOfRangeWarning):
                            vstyle = "color: #950000; border-width: 2px"
                            break
                    else:
                        vstyle = "border-width: 2px"
                self.doubleSpinBox_visc.setStyleSheet(vstyle)
                self.doubleSpinBox_visc.setValue(visc)
                self.doubleSpinBox_visc.setEnabled(True)
        else:  # feature
            self.doubleSpinBox_temp.setValue(np.nan)
            self.doubleSpinBox_temp.setEnabled(False)
            self.doubleSpinBox_visc.setValue(np.nan)
            self.doubleSpinBox_visc.setEnabled(False)

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
            slot_state = self.pipeline.slots[slot_index].__getstate__()
            self.__setstate__(slot_state)
            # determine whether we already have a medium defined
            cfg = meta_tool.get_rtdc_config(slot_state["path"])
            if "medium" in cfg["setup"]:
                medium = cfg["setup"]["medium"]
                idx = self.comboBox_medium.findData(medium)
                if idx < 0:
                    raise ValueError("Invalid medium: {}".format(medium))
                self.comboBox_medium.setCurrentIndex(idx)
                self.comboBox_medium.setEnabled(False)  # prevent modification
                # compute viscosity if possible
                self.on_medium()
                self.on_temperature()
            else:
                self.comboBox_medium.setEnabled(True)
                self.on_medium()
        else:
            self.setEnabled(False)

    def write_slot(self):
        """Update the shapeout2.pipeline.Dataslot instance"""
        # get current index
        slot_state = self.__getstate__()
        slot = self.pipeline.get_slot(slot_state["identifier"])
        # This is important, otherwise update_content will not have the
        # latest state.
        slot.__setstate__(slot_state)
        self.update_content()  # update slot combobox and visible fl names
        self.slot_changed.emit(slot_state)
