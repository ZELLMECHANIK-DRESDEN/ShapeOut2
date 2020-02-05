"""Test of Quick View functionalities

Created a new test file because putting "test_no_events_issue_37" and
"test_update_polygon_filter_issue_26" in one file raised an error
"RuntimeError: wrapped C/C++ object of type MatrixElement has been
deleted" (similar to issue #38).
"""
import pathlib

from PyQt5 import QtCore

import numpy as np
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


def test_no_events_issue_37(qtbot):
    """https://github.com/ZELLMECHANIK-DRESDEN/ShapeOut2/issues/37

    "ValueError: zero-size array to reduction operation minimum
    which has no identity" when all events are filtered out.
    """
    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # add a dataslot
    path = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"
    mw.add_dataslot(paths=[path, path])

    assert len(mw.pipeline.slot_ids) == 2, "we added those"
    assert len(mw.pipeline.filter_ids) == 1, "automatically added"

    # activate a dataslot
    slot_id = mw.pipeline.slot_ids[0]
    filt_id = mw.pipeline.filter_ids[0]
    em = mw.block_matrix.get_widget(slot_id, filt_id)
    qtbot.mouseClick(em, QtCore.Qt.LeftButton)  # activate
    # did that work?
    assert mw.pipeline.is_element_active(slot_id, filt_id)

    # filter away all events
    fe = mw.block_matrix.get_widget(filt_plot_id=filt_id)
    qtbot.mouseClick(fe.toolButton_modify, QtCore.Qt.LeftButton)
    fv = mw.widget_ana_view.widget_filter
    qtbot.mouseClick(fv.toolButton_moreless, QtCore.Qt.LeftButton)
    rc = fv._box_range_controls["area_um"]
    qtbot.mouseClick(rc.checkBox, QtCore.Qt.LeftButton)
    # did that work?
    assert rc.checkBox.isChecked()
    qtbot.mouseClick(fv.toolButton_moreless, QtCore.Qt.LeftButton)
    # set range
    rc.doubleSpinBox_min.setValue(0)
    rc.doubleSpinBox_max.setValue(1)
    qtbot.mouseClick(fv.pushButton_apply, QtCore.Qt.LeftButton)
    # did that work?
    ds = mw.pipeline.get_dataset(slot_index=0, filt_index=0,
                                 apply_filter=True)
    assert np.sum(ds.filter.all) == 0

    # open QuickView
    slot_id = mw.pipeline.slot_ids[0]
    filt_id = mw.pipeline.filter_ids[0]
    em = mw.block_matrix.get_widget(slot_id, filt_id)

    # this raised the error
    qtbot.mouseClick(em, QtCore.Qt.LeftButton, QtCore.Qt.ShiftModifier)
    mw.close()
