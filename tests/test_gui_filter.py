"""Test of filter functionalities"""
import copy
import pathlib
import tempfile

import dclab
import numpy as np
from PyQt5 import QtCore

from shapeout2.gui.main import ShapeOut2
from shapeout2 import session
import pytest


@pytest.fixture(autouse=True)
def run_around_tests():
    # Code that will run before your test, for example:
    session.clear_session()
    # A test function will be run at this point
    yield
    # Code that will run after your test, for example:
    session.clear_session()


def test_filter_min_max_inf(qtbot):
    # generate fake dataset
    path = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"
    with dclab.new_dataset(path) as ds:
        config = copy.deepcopy(ds.config)

    tmp = tempfile.mktemp(".rtdc", prefix="example_filter_inf_")
    ds2 = dclab.new_dataset({"deform": np.linspace(0, .01, 100),
                             "area_um": np.linspace(20, 200, 100),
                             "area_ratio": np.linspace(1, 1.1, 100)
                             })
    ds2.config.update(config)
    ds2["area_ratio"][0] = np.inf
    ds2["area_ratio"][1] = np.nan
    ds2.export.hdf5(tmp, features=["area_um", "deform", "area_ratio"])

    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # add the file
    mw.add_dataslot(paths=[tmp])

    assert len(mw.pipeline.slot_ids) == 1, "we added that"
    assert len(mw.pipeline.filter_ids) == 1, "automatically added"

    # open the filter edit in the Analysis View
    fe = mw.block_matrix.get_widget(filt_plot_id=mw.pipeline.filter_ids[0])
    qtbot.mouseClick(fe.toolButton_modify, QtCore.Qt.LeftButton)

    # box filtering
    wf = mw.widget_ana_view.widget_filter
    # enable selection
    qtbot.mouseClick(wf.toolButton_moreless, QtCore.Qt.LeftButton)
    # find the porosity item and click the checkbox
    rc = wf._box_range_controls["area_ratio"]
    qtbot.mouseClick(rc.checkBox, QtCore.Qt.LeftButton)
    # disable selection
    qtbot.mouseClick(wf.toolButton_moreless, QtCore.Qt.LeftButton)

    # check that the range control does not have all-zero values
    rcstate = rc.__getstate__()
    assert rcstate["start"] != 0
    assert rcstate["end"] != 0
    # only approximate (b/c they were converted on the range scale)
    assert np.allclose(rcstate["start"], ds2["area_ratio"][2], rtol=1e-4)
    assert np.allclose(rcstate["end"], 1.1, rtol=1e-4)

    try:
        pathlib.Path(tmp).unlink()
    except BaseException:
        pass
