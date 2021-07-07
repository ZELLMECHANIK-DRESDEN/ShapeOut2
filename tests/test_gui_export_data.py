"""Test data export"""
import pathlib
import tempfile
from unittest import mock

from PyQt5 import QtCore, QtWidgets
import pytest
from shapeout2.gui.main import ShapeOut2
from shapeout2.gui import export
from shapeout2 import session


data_path = pathlib.Path(__file__).parent / "data"


@pytest.fixture(autouse=True)
def run_around_tests():
    # Code that will run before your test, for example:
    session.clear_session()
    # A test function will be run at this point
    yield
    # Code that will run after your test, for example:
    session.clear_session()


def test_export_datasets_rtdc(qtbot):
    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # add 3 dataslots
    path = data_path / "calibration_beads_47.rtdc"
    mw.add_dataslot(paths=[path, path, path])

    # perform the export
    tmpd = tempfile.mkdtemp(prefix="shapeout2_test_data_export_")
    with mock.patch.object(QtWidgets.QFileDialog, "getExistingDirectory",
                           return_value=tmpd):

        # create export dialog manually (asks user for directory)
        dlg = export.ExportData(mw, pipeline=mw.pipeline)

        # Everything is set-up already (.rtdc export, all features selected).
        # Click OK.
        buttons = dlg.buttonBox.buttons()
        qtbot.mouseClick(buttons[0], QtCore.Qt.LeftButton)

    # make sure we have three .rtdc files
    assert len(list(pathlib.Path(tmpd).glob("*.rtdc"))) == 3
