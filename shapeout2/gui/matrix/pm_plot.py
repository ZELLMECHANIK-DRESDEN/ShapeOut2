import pkg_resources

from PyQt5 import uic, QtCore, QtWidgets


class MatrixPlot(QtWidgets.QWidget):
    _instance_counter = 0
    active_toggled = QtCore.pyqtSignal()
    option_action = QtCore.pyqtSignal(str)

    def __init__(self, title="FS?"):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.matrix", "pm_plot.ui")
        uic.loadUi(path_ui, self)

        MatrixPlot._instance_counter += 1
        self.identifier = "p{}".format(MatrixPlot._instance_counter)
        self.title = title

        # options button
        menu = QtWidgets.QMenu()
        menu.addAction('duplicate', self.action_duplicate)
        menu.addAction('remove', self.action_remove)
        self.pushButton_opt.setMenu(menu)

        # toggle all active, all inactive, semi state
        self.pushButton_toggle.clicked.connect(self.active_toggled.emit)

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
        self.option_action.emit("duplicate")

    def action_remove(self):
        self.option_action.emit("remove")

    def update_content(self):
        """Reset tool tips and title"""
        self.label.setToolTip(self.title)
        if len(self.title) > 8:
            title = self.title[:5]+"..."
        else:
            title = self.title
        self.label.setText(title)
