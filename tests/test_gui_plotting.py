"""Test of data set functionalities"""
import pathlib

import numpy as np
from PyQt5 import QtCore
import pytest
from shapeout2.gui.main import ShapeOut2
from shapeout2 import pipeline, session


@pytest.fixture(autouse=True)
def run_around_tests():
    # Code that will run before your test, for example:
    session.clear_session()
    # A test function will be run at this point
    yield
    # Code that will run after your test, for example:
    session.clear_session()


def test_handle_empty_plots_issue_27(qtbot):
    """Correctly handle empty plots

    https://github.com/ZELLMECHANIK-DRESDEN/ShapeOut2/issues/27
    """
    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # add a dataslot
    path = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"
    mw.add_dataslot(paths=[path])
    # add another one
    mw.add_dataslot(paths=[path])

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

    # now create a plot window
    plot_id = mw.add_plot()
    pe = mw.block_matrix.get_widget(slot_id, plot_id)
    with pytest.warns(pipeline.core.EmptyDatasetWarning):
        # this now only throws a warning
        qtbot.mouseClick(pe, QtCore.Qt.LeftButton)  # activate (raises #27)


def test_remove_plots_issue_36(qtbot):
    """Correctly handle empty plots

    https://github.com/ZELLMECHANIK-DRESDEN/ShapeOut2/issues/36

    Traceback (most recent call last):
      File "/home/paul/repos/ShapeOut2/shapeout2/gui/main.py",
        line 193, in adopt_pipeline
        lay = pipeline_state["plots"][plot_index]["layout"]
    IndexError: list index out of range
    """
    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # add a dataslots
    path = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"
    mw.add_dataslot(paths=[path, path, path])

    assert len(mw.pipeline.slot_ids) == 3, "we added those"
    assert len(mw.pipeline.filter_ids) == 1, "automatically added"

    # now create a plot window
    plot_id = mw.add_plot()
    # and another one
    mw.add_plot()

    # remove a plot
    pw = mw.block_matrix.get_widget(filt_plot_id=plot_id)
    pw.action_remove()
