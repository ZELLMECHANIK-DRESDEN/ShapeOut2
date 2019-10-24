import pkg_resources

from PyQt5 import uic, QtCore, QtWidgets

from ... import pipeline


class MatrixPlot(QtWidgets.QWidget):
    active_toggled = QtCore.pyqtSignal()
    option_action = QtCore.pyqtSignal(str)
    modify_clicked = QtCore.pyqtSignal(str)

    def __init__(self, identifier=None, state=None):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.matrix", "pm_plot.ui")
        uic.loadUi(path_ui, self)

        # options button
        menu = QtWidgets.QMenu()
        menu.addAction('duplicate', self.action_duplicate)
        menu.addAction('remove', self.action_remove)
        self.toolButton_opt.setMenu(menu)

        # toggle all active, all inactive, semi state
        self.toolButton_toggle.clicked.connect(self.active_toggled.emit)
        self.toolButton_modify.clicked.connect(self.on_modify)

        if state is None:
            plot = pipeline.Plot._instances[identifier]
            self.identifier = identifier
            self.name = plot.name
            # set tooltip/label
            self.update_content()
        else:
            self.__setstate__(state)

    def __getstate__(self):
        state = {"name": self.name,
                 "identifier": self.identifier,
                 }
        return state

    def __setstate__(self, state):
        self.identifier = state["identifier"]
        self.name = state["name"]
        self.update_content()

    @property
    def name(self):
        plot = pipeline.Plot._instances[self.identifier]
        return plot.name

    @name.setter
    def name(self, text):
        plot = pipeline.Plot._instances[self.identifier]
        plot.name = text

    def action_duplicate(self):
        self.option_action.emit("duplicate")

    def action_remove(self):
        self.option_action.emit("remove")

    def on_modify(self):
        self.modify_clicked.emit(self.identifier)

    @QtCore.pyqtSlot()
    def update_content(self):
        """Reset tool tips and title"""
        self.label.setToolTip(self.name)
        if len(self.name) > 8:
            title = self.name[:5]+"..."
        else:
            title = self.name
        self.label.setText(title)
