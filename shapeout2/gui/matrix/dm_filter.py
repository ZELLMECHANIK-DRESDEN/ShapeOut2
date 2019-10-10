import pkg_resources

from PyQt5 import uic, QtCore, QtWidgets


class MatrixFilter(QtWidgets.QWidget):
    _instance_counter = 0
    active_toggled = QtCore.pyqtSignal()
    enabled_toggled = QtCore.pyqtSignal(bool)
    option_action = QtCore.pyqtSignal(str)

    def __init__(self, name="FS?"):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.matrix", "dm_filter.ui")
        uic.loadUi(path_ui, self)

        MatrixFilter._instance_counter += 1
        self.identifier = "f{}".format(MatrixFilter._instance_counter)
        self.name = name

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
        state = {"identifier": self.identifier,
                 "enabled": self.checkBox.isChecked(),
                 "name": self.name,
                 }
        return state

    def __setstate__(self, state):
        self.identifier = state["identifier"]
        self.name = state["name"]
        self.checkBox.setChecked(state["enabled"])
        self.update_content()

    def action_duplicate(self):
        self.option_action.emit("duplicate")

    def action_remove(self):
        self.option_action.emit("remove")

    def update_content(self):
        """Reset tool tips and title"""
        self.label.setToolTip(self.name)
        if len(self.name) > 8:
            title = self.name[:5]+"..."
        else:
            title = self.name
        self.label.setText(title)
