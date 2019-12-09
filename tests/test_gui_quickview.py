"""Test of data set functionalities"""
import pathlib

from PyQt5 import QtCore

from shapeout2.gui.main import ShapeOut2


def test_simple(qtbot):
    """Open the main window and close it again"""
    main_window = ShapeOut2()
    main_window.close()


def test_quickview_issue_25(qtbot):
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
