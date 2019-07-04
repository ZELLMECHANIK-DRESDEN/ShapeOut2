import pkg_resources

from PyQt5 import uic, QtCore, QtWidgets


class MatrixFilter(QtWidgets.QWidget):
    _instance_counter = 0
    active_toggled = QtCore.pyqtSignal()
    enabled_toggled = QtCore.pyqtSignal()

    def __init__(self, title="FS?"):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "matrix_filter.ui")
        uic.loadUi(path_ui, self)

        MatrixFilter._instance_counter += 1
        self.identifier = "f{}".format(MatrixFilter._instance_counter)
        self.title = title

        # options button
        menu = QtWidgets.QMenu()
        menu.addAction('duplicate', self.action_duplicate)
        menu.addAction('remove', self.action_remove)
        self.pushButton_opt.setMenu(menu)

        # toggle all active, all inactive, semi state
        self.pushButton_toggle.clicked.connect(self.active_toggled.emit)

        # toggle enabled/disabled state
        self.checkBox.clicked.connect(self.enabled_toggled.emit)

        # set tooltip/label
        self.update_content()

    def __getstate__(self):
        state = {"title": self.title,
                 "identifier": self.identifier,
                 }
        return state

    def __setstate__(self, state):
        self.identifier = state["identifier"]
        self.title = state["title"]
        self.update_content()

    def action_duplicate(self):
        pass

    def action_remove(self):
        pass

    def update_content(self):
        """Reset tool tips and title"""
        self.label.setToolTip(self.title)
        if len(self.title) > 8:
            title = self.title[:5]+"..."
        else:
            title = self.title
        self.label.setText(title)
