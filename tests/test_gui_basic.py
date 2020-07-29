"""Test of data set functionalities"""
import pathlib

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


def test_simple(qtbot):
    """Open the main window and close it again"""
    main_window = ShapeOut2()
    main_window.close()


def test_matrix_slots(qtbot):
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
    qtbot.mouseClick(em, QtCore.Qt.LeftButton)
    # did that work?
    assert mw.pipeline.is_element_active(slot_id, filt_id)
    slot_id2 = mw.pipeline.slot_ids[1]
    assert not mw.pipeline.is_element_active(slot_id2, filt_id)

    # remove a dataslot
    wd = mw.block_matrix.get_widget(slot_id=slot_id)
    wd.action_remove()
    assert not mw.pipeline.is_element_active(slot_id2, filt_id)
