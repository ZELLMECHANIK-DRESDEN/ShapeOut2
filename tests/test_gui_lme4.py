"""Test lme4 functionality"""
import pathlib

from shapeout2.gui.main import ShapeOut2
from shapeout2 import session
from shapeout2.gui.compute.comp_lme4 import ComputeSignificance
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


def test_lme4_with_dcor_session(qtbot):
    """
    Open a session with DCOR data and perform lme4 analysis from
    dclab docs at
    https://dclab.readthedocs.io/en/stable/sec_av_lme4.html
    """
    mw = ShapeOut2()
    qtbot.addWidget(mw)
    mw.on_action_open(data_path / "version_2_5_0_dcor_lme4.so2")

    # create dialog manually
    dlg = ComputeSignificance(mw, pipeline=mw.pipeline)

    # set the variables
    # treatment rep 1
    dlg.datasets[0].comboBox_group.setCurrentIndex(1)
    # treatment rep 2
    dlg.datasets[1].comboBox_group.setCurrentIndex(1)
    dlg.datasets[0].spinBox_repeat.setValue(2)
    # control rep 1
    pass
    # control rep 2
    dlg.datasets[3].spinBox_repeat.setValue(2)
    # control rep 3
    dlg.datasets[4].spinBox_repeat.setValue(3)

    # set the feature
    feat_id = dlg.comboBox_feat.findData("deform")
    dlg.comboBox_feat.setCurrentIndex(feat_id)

    dlgr = dlg.on_lme4(ret_dlg=True)

    assert dlgr.lineEdit_pvalue.text() == "0.012969"
