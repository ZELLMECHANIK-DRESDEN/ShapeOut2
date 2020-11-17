"""Screenshots for quick guide emodulus"""
import os
import sys
import tempfile

import dclab
import h5py
import numpy as np
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from shapeout2.gui.main import ShapeOut2

app = QApplication(sys.argv)

QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.C))

mw = ShapeOut2()
mw.settings.setValue("general/check for updates", 0)
mw.settings.setValue("advanced/check pyqtgraph version", 0)

# create a fake dataset
ds = dclab.new_dataset("Figure3_Blood_Initial.rtdc")
tmp = tempfile.mktemp(".rtdc", prefix="example_")
ds.export.hdf5(tmp, features=["deform", "area_um", "bright_avg"])
with h5py.File(tmp, mode="a") as h5:
    h5["events/temp"] = np.linspace(22, 23, len(ds))
    h5.attrs.pop("setup:medium")
    h5.attrs["setup:temperature"] = 22.5

# build up a session
mw.add_dataslot(paths=[tmp])
mw.reload_pipeline()

# analysis view
mw.on_modify_slot(mw.pipeline.slot_ids[0])
mw.widget_ana_view.repaint()
wsl = mw.widget_ana_view.widget_slot
wsl.groupBox_emod.setFixedSize(350, wsl.groupBox_emod.sizeHint().height())

wsl.comboBox_medium.setCurrentIndex(
    wsl.comboBox_medium.findData("CellCarrier"))
wsl.comboBox_temp.setCurrentIndex(wsl.comboBox_temp.findData("config"))
QApplication.processEvents()
wsl.groupBox_emod.grab().save("_qg_emodulus_config.png")

wsl.comboBox_medium.setCurrentIndex(
    wsl.comboBox_medium.findData("CellCarrier"))
wsl.comboBox_temp.setCurrentIndex(wsl.comboBox_temp.findData("feature"))
QApplication.processEvents()
wsl.groupBox_emod.grab().save("_qg_emodulus_feature.png")

wsl.comboBox_medium.setCurrentIndex(
    wsl.comboBox_medium.findData("CellCarrier"))
wsl.comboBox_temp.setCurrentIndex(wsl.comboBox_temp.findData("manual"))
wsl.doubleSpinBox_temp.setValue(31)
QApplication.processEvents()
wsl.groupBox_emod.grab().save("_qg_emodulus_badtemp.png")

wsl.comboBox_medium.setCurrentIndex(wsl.comboBox_medium.findData("other"))
wsl.doubleSpinBox_visc.setValue(3.14)
QApplication.processEvents()
wsl.groupBox_emod.grab().save("_qg_emodulus_other.png")

mw.close()

os.remove(tmp)
