import pkg_resources

from PyQt5 import uic, QtWidgets, QtCore

from .. import meta_tool


class MatrixDataset(QtWidgets.QWidget):
    _instance_counter = 0
    active_toggled = QtCore.pyqtSignal()
    enabled_toggled = QtCore.pyqtSignal()

    def __init__(self, path=None):
        """Create a new dataset matrix element

        If `path` is None, a dummy element is inserted which needs
        to be updated with :func:`MatrixDataset.__setstate__`.
        """
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "matrix_dataset.ui")
        uic.loadUi(path_ui, self)

        MatrixDataset._instance_counter += 1
        self.identifier = "ds{}".format(MatrixDataset._instance_counter)
        self.path = path

        # options button
        menu = QtWidgets.QMenu()
        menu.addAction('insert anew', self.action_insert_anew)
        menu.addAction('duplicate', self.action_duplicate)
        menu.addAction('remove', self.action_remove)
        self.pushButton_opt.setMenu(menu)

        # toggle all active, all inactive, semi state
        self.pushButton_toggle.clicked.connect(self.active_toggled.emit)

        # toggle enabled/disabled state
        self.checkBox.clicked.connect(self.enabled_toggled.emit)

        # set tooltip/label
        self.update_content()

        self.setFixedSize(QtCore.QSize(80, 80))
        self.resize(QtCore.QSize(80, 80))
        self.setMaximumSize(QtCore.QSize(80, 80))

    def __getstate__(self):
        state = {"path": self.path,
                 "identifier": self.identifier,
                 }
        return state

    def __setstate__(self, state):
        self.identifier = state["identifier"]
        self.path = state["path"]
        self.update_content()

    def action_duplicate(self):
        pass

    def action_insert_anew(self):
        pass

    def action_remove(self):
        pass

    def update_content(self):
        """Reset tool tips and title"""
        if self.path is not None:
            title = meta_tool.get_repr(self.path, append_path=True)
            self.setToolTip(title)
            self.label.setToolTip(title)
            if len(title) > 8:
                title = title[:5] + "..."
            self.label.setText(title)
