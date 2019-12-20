"""Test of data set functionalities"""
import pathlib

from PyQt5 import QtCore

import dclab
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


def test_simple(qtbot):
    """Open the main window and close it again"""
    main_window = ShapeOut2()
    main_window.close()


def test_clear_session_issue_25(qtbot):
    """https://github.com/ZELLMECHANIK-DRESDEN/ShapeOut2/issues/25"""
    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # add a dataslot
    path = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"
    mw.add_dataslot(paths=[path])

    assert len(mw.pipeline.slot_ids) == 1, "we added that"
    assert len(mw.pipeline.filter_ids) == 1, "automatically added"

    # activate a dataslot
    slot_id = mw.pipeline.slot_ids[0]
    filt_id = mw.pipeline.filter_ids[0]
    em = mw.block_matrix.get_widget(slot_id, filt_id)
    qtbot.mouseClick(em, QtCore.Qt.LeftButton, QtCore.Qt.ShiftModifier)
    # did that work?
    assert mw.toolButton_quick_view.isChecked()

    # now clear the session (this raised the errror in #25)
    mw.on_action_clear(assume_yes=True)


def test_update_polygon_filter_issue_26(qtbot):
    """https://github.com/ZELLMECHANIK-DRESDEN/ShapeOut2/issues/26"""
    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # add a dataslot
    path = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"
    mw.add_dataslot(paths=[path])

    assert len(mw.pipeline.slot_ids) == 1, "we added that"
    assert len(mw.pipeline.filter_ids) == 1, "automatically added"

    # activate a dataslot
    slot_id = mw.pipeline.slot_ids[0]
    filt_id = mw.pipeline.filter_ids[0]
    em = mw.block_matrix.get_widget(slot_id, filt_id)
    qtbot.mouseClick(em, QtCore.Qt.LeftButton)  # activate
    qtbot.mouseClick(em, QtCore.Qt.LeftButton, QtCore.Qt.ShiftModifier)
    # did that work?
    assert mw.toolButton_quick_view.isChecked()

    # Add a polygon filter
    assert len(dclab.PolygonFilter.instances) == 0
    qv = mw.widget_quick_view
    qtbot.mouseClick(qv.toolButton_poly, QtCore.Qt.LeftButton)
    qtbot.mouseClick(qv.pushButton_poly_create, QtCore.Qt.LeftButton)
    # three positions (not sure how to do this with mouse clicks)
    points = [[22, 0.01],
              [30, 0.01],
              [30, 0.014],
              ]
    qv.widget_scatter.set_poly_points(points)
    qtbot.mouseClick(qv.pushButton_poly_save, QtCore.Qt.LeftButton)
    # did that work?
    assert len(dclab.PolygonFilter.instances) == 1
    pf = dclab.PolygonFilter.instances[0]
    assert np.allclose(pf.points, points)

    # Add the polygon filter to the first filter
    fe = mw.block_matrix.get_widget(filt_plot_id=filt_id)
    qtbot.mouseClick(fe.toolButton_modify, QtCore.Qt.LeftButton)
    fv = mw.widget_ana_view.widget_filter
    cb = fv._polygon_checkboxes[pf.unique_id]
    qtbot.mouseClick(cb, QtCore.Qt.LeftButton)
    assert cb.isChecked()
    qtbot.mouseClick(fv.pushButton_apply, QtCore.Qt.LeftButton)
    # did that work?
    ds = mw.pipeline.get_dataset(slot_index=0, filt_index=0,
                                 apply_filter=True)
    assert np.sum(ds.filter.all) == 15

    # Modify the polygon filter
    qv.comboBox_poly.setCurrentIndex(1)
    points2 = [[22, 0.01],
               [30, 0.01],
               [30, 0.012],
               ]
    qv.widget_scatter.set_poly_points(points2)
    qtbot.mouseClick(qv.pushButton_poly_save, QtCore.Qt.LeftButton)
    assert len(dclab.PolygonFilter.instances) == 1
    pf2 = dclab.PolygonFilter.instances[0]
    assert np.allclose(pf2.points, points2)
    assert pf is pf2
    # now the filter should be updated (this worked already)
    ds2 = mw.pipeline.get_dataset(slot_index=0, filt_index=0,
                                  apply_filter=True)
    assert np.sum(ds2.filter.all) == 8
    # but the plots were not updated in #26
    assert len(qv.widget_scatter.scatter.getData()[0]) == 8
