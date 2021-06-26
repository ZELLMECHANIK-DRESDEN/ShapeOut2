import io
import pathlib
from unittest import mock
import sys

from PyQt5 import QtCore

import shapeout2
from shapeout2.gui.main import ShapeOut2
from shapeout2 import session
import pytest


data_path = pathlib.Path(__file__).parent / "data"


@pytest.fixture(autouse=True)
def run_around_tests():
    # Code that will run before your test, for example:
    session.clear_session()
    # A test function will be run at this point
    yield
    # Code that will run after your test, for example:
    session.clear_session()


@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python>=3.8")
def test_init_print_version(qtbot):
    mock_stdout = io.StringIO()
    mock_exit = mock.Mock()

    with mock.patch("sys.exit", mock_exit):
        with mock.patch('sys.stdout', mock_stdout):
            mw = ShapeOut2("--version")
            mw.close()

    assert mock_exit.call_args.args[0] == 0
    assert mock_stdout.getvalue().strip() == shapeout2.__version__


@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python>=3.8")
def test_init_load_session(qtbot):
    mw = ShapeOut2(data_path / "version_2_1_0_basic.so2")
    assert len(mw.pipeline.slots) == 1
    assert len(mw.pipeline.filters) == 1
    mw.close()


@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python>=3.8")
def test_init_load_dataslot(qtbot):
    mw = ShapeOut2(data_path / "calibration_beads_47.rtdc")
    assert len(mw.pipeline.slots) == 1
    assert len(mw.pipeline.filters) == 1
    mw.close()


@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python>=3.8")
def test_on_action_about(qtbot):
    with mock.patch("PyQt5.QtWidgets.QMessageBox.about") as mock_about:
        mw = ShapeOut2()
        mw.on_action_about()
        mw.close()

        assert mock_about.call_args.args[1] == \
               f"Shape-Out {shapeout2.__version__}"
        assert "Shape-Out 2" in mock_about.call_args.args[2]


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
