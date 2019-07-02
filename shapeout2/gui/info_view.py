import pkg_resources

from PyQt5 import uic, QtWidgets

from ..external import pyqtgraph as pg


class InfoView(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "info_view.ui")
        uic.loadUi(path_ui, self)
        self.setWindowTitle("Info View")

    def show(self, path):
        pass