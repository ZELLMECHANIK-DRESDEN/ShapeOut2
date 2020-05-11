"""Test computation of emodulus"""
import pathlib
import tempfile

from PyQt5 import QtCore, QtWidgets

import dclab
import h5py
import numpy as np
from shapeout2.gui.main import ShapeOut2
from shapeout2 import session
import pytest


def make_dataset(medium="CellCarrier", temp=22.5, temp_range=[22, 23],
                 chip_region="channel"):
    # create a fake dataset
    path = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"
    ds = dclab.new_dataset(path)
    tmp = tempfile.mktemp(".rtdc", prefix="example_")
    ds.export.hdf5(tmp, features=["deform", "area_um", "bright_avg"])
    with h5py.File(tmp, mode="a") as h5:
        h5["events/temp"] = np.linspace(temp_range[0], temp_range[1], len(ds))
        h5.attrs["setup:medium"] = medium
        h5.attrs["setup:temperature"] = temp
        h5.attrs["setup:chip region"] = chip_region
    return pathlib.Path(tmp)


@pytest.fixture(autouse=True)
def run_around_tests():
    # Code that will run before your test, for example:
    session.clear_session()
    # A test function will be run at this point
    yield
    # Code that will run after your test, for example:
    session.clear_session()


@pytest.mark.filterwarnings(
    'ignore::dclab.features.emodulus.YoungsModulusLookupTableExceededWarning')
def test_simple(qtbot):
    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # add fake measurement
    path = make_dataset(medium="CellCarrier", temp=22.5, temp_range=[22, 23])

    with dclab.new_dataset(path) as ds:
        # Youngs modulus can readily be computed
        # https://dclab.readthedocs.io/en/latest/sec_av_emodulus.html
        ds.config["calculation"]["emodulus medium"] = \
            ds.config["setup"]["medium"]
        ds.config["calculation"]["emodulus model"] = "elastic sphere"
        emodA = np.array(ds["emodulus"], copy=True)
        ds.config["calculation"]["emodulus temperature"] = \
            ds.config["setup"]["temperature"]
        emodC = np.array(ds["emodulus"], copy=True)
        assert not np.allclose(emodA, emodC, atol=0, rtol=1e-12,
                               equal_nan=True), "sanity check"

    mw.add_dataslot(paths=[path])
    wsl = mw.widget_ana_view.widget_slot

    # default values
    assert wsl.comboBox_medium.currentData() == "CellCarrier"
    assert wsl.comboBox_temp.currentData() == "feature"

    # scenario A (this is already set by default)
    ds1 = mw.pipeline.slots[0].get_dataset()
    assert np.allclose(ds1["emodulus"], emodA, atol=0, rtol=1e-12,
                       equal_nan=True)

    # scenario C (switch to config)
    wsl.comboBox_temp.setCurrentIndex(wsl.comboBox_temp.findData("config"))
    qtbot.mouseClick(wsl.pushButton_apply, QtCore.Qt.LeftButton)
    ds2 = mw.pipeline.slots[0].get_dataset()
    assert np.allclose(ds2["emodulus"], emodC, atol=0, rtol=1e-12,
                       equal_nan=True)

    # scenario C (switch to manual)
    wsl.comboBox_temp.setCurrentIndex(wsl.comboBox_temp.findData("manual"))
    wsl.doubleSpinBox_temp.setValue(22.5)
    qtbot.mouseClick(wsl.pushButton_apply, QtCore.Qt.LeftButton)
    ds3 = mw.pipeline.slots[0].get_dataset()
    assert np.allclose(ds3["emodulus"], emodC, atol=0, rtol=1e-12,
                       equal_nan=True)

    try:
        path.unlink()
    except BaseException:
        pass


def test_switch_and_update(qtbot):
    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # add fake measurement
    path1 = make_dataset(medium="CellCarrier", temp=22.5, temp_range=[22, 23],
                         chip_region="channel")
    path2 = make_dataset(medium="CellCarrier", temp=22.5, temp_range=[22, 23],
                         chip_region="reservoir")

    slot_id1, slot_id2 = mw.add_dataslot(paths=[path1, path2])
    wsl = mw.widget_ana_view.widget_slot

    # select the first slot
    em1 = mw.block_matrix.get_widget(slot_id=slot_id1)
    em2 = mw.block_matrix.get_widget(slot_id=slot_id2)
    qtbot.mouseClick(em1.toolButton_modify, QtCore.Qt.LeftButton)
    # set temperature manually
    idm = wsl.comboBox_temp.findData("manual")
    wsl.comboBox_temp.setCurrentIndex(idm)
    assert wsl.comboBox_temp.currentData() == "manual"
    wsl.doubleSpinBox_temp.setValue(20.0)
    assert wsl.doubleSpinBox_temp.value() == 20
    qtbot.mouseClick(wsl.pushButton_apply, QtCore.Qt.LeftButton)
    QtWidgets.QApplication.processEvents()
    # check whether that worked
    assert wsl.get_dataset(
    ).config["calculation"]["emodulus temperature"] == 20

    # switch to the second (reservoir) measurement
    qtbot.mouseClick(em2.toolButton_modify, QtCore.Qt.LeftButton)
    assert not wsl.groupBox_emod.isVisible()
    # now switch back
    qtbot.mouseClick(em1.toolButton_modify, QtCore.Qt.LeftButton)

    # This is the actual test
    assert wsl.doubleSpinBox_temp.value() == 20

    try:
        path1.unlink()
        path2.unlink()
    except BaseException:
        pass
