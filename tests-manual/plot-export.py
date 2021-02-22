"""Referemce plotting image tests"""
from unittest import mock
import pathlib
import sys

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from shapeout2.gui import export
from shapeout2.gui.main import ShapeOut2


here = pathlib.Path(__file__).parent

# instantiate Shape-Out
app = QApplication(sys.argv)
QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.C))
mw = ShapeOut2()

# load session
mw.on_action_open(here / "plot-export.so2")

# scatter-and-contour-export
with mock.patch("PyQt5.QtWidgets.QFileDialog.getSaveFileName") as gsfn:
    gsfn.return_value = \
        (str(here / "plot-export_scatter-and-contour-export_actual.png"),
         ".png")
    # create export dialog manually
    dlg = export.ExportPlot(mw, pipeline=mw.pipeline)
    # select a single plot to export
    plot_id = mw.pipeline.plot_ids[0]
    plot_index = dlg.comboBox_plot.findData(plot_id)
    dlg.comboBox_plot.setCurrentIndex(plot_index)
    dlg.export_plots()
