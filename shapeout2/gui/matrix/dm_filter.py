import pkg_resources

from PyQt5 import uic, QtCore, QtWidgets

from ... import filter


class MatrixFilter(QtWidgets.QWidget):
    active_toggled = QtCore.pyqtSignal()
    enabled_toggled = QtCore.pyqtSignal(bool)
    option_action = QtCore.pyqtSignal(str)

    def __init__(self, name=None, identifier=None, state=None):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.matrix", "dm_filter.ui")
        uic.loadUi(path_ui, self)

        # options button
        menu = QtWidgets.QMenu()
        menu.addAction('duplicate', self.action_duplicate)
        menu.addAction('remove', self.action_remove)
        self.toolButton_opt.setMenu(menu)

        # toggle all active, all inactive, semi state
        self.toolButton_toggle.clicked.connect(self.active_toggled.emit)

        # toggle enabled/disabled state
        self.checkBox.clicked.connect(self.on_enabled_toggled)

        if state is None:
            if identifier is None:
                # get the identifier from the filter class
                identifier = filter.Filter().identifier
            self.identifier = identifier
            if name is None:
                name = identifier
            self.name = name
            # set tooltip/label
            self.update_content()
        else:
            self.__setstate__(state)

    @property
    def enabled(self):
        filt = filter.Filter._instances[self.identifier]
        return filt.general["enable filters"]

    @enabled.setter
    def enabled(self, b):
        filt = filter.Filter._instances[self.identifier]
        filt.general["enable filters"] = b

    @property
    def name(self):
        filt = filter.Filter._instances[self.identifier]
        return filt.name

    @name.setter
    def name(self, text):
        filt = filter.Filter._instances[self.identifier]
        filt.name = text

    def __getstate__(self):
        state = {"enabled": self.enabled,
                 "identifier": self.identifier,
                 "name": self.name,
                 }
        return state

    def __setstate__(self, state):
        if state["identifier"] not in filter.Filter._instances:
            # Create a new filter with the identifier
            filter.Filter(identifier=state["identifier"])
        self.identifier = state["identifier"]
        self.enabled = state["enabled"]
        self.name = state["name"]
        self.update_content()

    def action_duplicate(self):
        self.option_action.emit("duplicate")

    def action_remove(self):
        self.option_action.emit("remove")

    def on_enabled_toggled(self, b):
        self.enabled = b
        self.enabled_toggled.emit(b)

    @QtCore.pyqtSlot()
    def update_content(self):
        """Reset tool tips and title"""
        self.label.setToolTip(self.name)
        if len(self.name) > 8:
            title = self.name[:5]+"..."
        else:
            title = self.name
        self.checkBox.blockSignals(True)
        self.checkBox.setChecked(self.enabled)
        self.checkBox.blockSignals(False)
        self.enabled_toggled.emit(self.enabled)
        self.label.setText(title)
