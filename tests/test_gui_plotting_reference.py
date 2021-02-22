"""Referemce plotting image tests"""
import os
import pathlib
import tempfile

import imageio
import numpy as np
from PyQt5 import QtWidgets
import pytest
from shapeout2.gui import export
from shapeout2.gui.main import ShapeOut2
from shapeout2 import session


data_path = pathlib.Path(__file__).parent / "data"
dref_path = data_path / "plotting_reference"


@pytest.fixture(autouse=True)
def run_around_tests():
    # Code that will run before your test, for example:
    session.clear_session()
    # A test function will be run at this point
    yield
    # Code that will run after your test, for example:
    session.clear_session()


def assert_images_are_equal(path1, path2):
    """Checks whether the image data of two images match"""
    data1 = imageio.imread(path1)
    data2 = imageio.imread(path2)
    assert np.all(data1 == data2)


def test_reference_scatter_and_contour_export(qtbot, monkeypatch):
    """Export the first plot and check with reference"""
    mw = ShapeOut2()
    qtbot.addWidget(mw)
    mw.on_action_open(data_path / "version_2_5_0_plotting_reference.so2")

    # perform the export
    tmpd = tempfile.mkdtemp(suffix="", prefix="shapeout2_test_plot_export_")

    tmpf = os.path.join(tmpd, "_scatter-and-contour-export.png")
    assert not pathlib.Path(tmpf).exists()
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName",
                        lambda *args: (tmpf, ""))

    # create export dialog manually
    dlg = export.ExportPlot(mw, pipeline=mw.pipeline)
    # select a single plot to export
    plot_id = mw.pipeline.plot_ids[0]
    plot_index = dlg.comboBox_plot.findData(plot_id)
    dlg.comboBox_plot.setCurrentIndex(plot_index)
    exported_plots = dlg.export_plots()
    assert_images_are_equal(exported_plots[plot_id],
                            dref_path / "scatter-and-contour-export.png")
