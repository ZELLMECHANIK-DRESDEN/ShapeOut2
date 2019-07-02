import pkg_resources

from PyQt5 import uic, QtWidgets, QtCore

from .. import meta_tool


class MatrixDataset(QtWidgets.QWidget):
    def __init__(self, path):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "matrix_dataset.ui")
        uic.loadUi(path_ui, self)

        title = meta_tool.get_repr(path, append_path=True)
        self.path = path

        self.setFixedSize(QtCore.QSize(80, 80))
        self.resize(QtCore.QSize(80, 80))
        self.setMaximumSize(QtCore.QSize(80, 80))

        self.setToolTip(title)
        self.label.setToolTip(title)
        if len(title) > 8:
            title = title[:5] + "..."
        self.label.setText(title)
