import pkg_resources

from PyQt5 import uic, QtWidgets


class PlotPanel(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "ana_plot.ui")
        uic.loadUi(path_ui, self)
