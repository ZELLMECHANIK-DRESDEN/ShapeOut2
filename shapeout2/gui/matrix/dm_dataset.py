import pkg_resources

from PyQt5 import uic, QtWidgets, QtCore

from ... import meta_tool
from ... import pipeline


class MatrixDataset(QtWidgets.QWidget):
    active_toggled = QtCore.pyqtSignal()
    enabled_toggled = QtCore.pyqtSignal(bool)
    option_action = QtCore.pyqtSignal(str)
    modify_clicked = QtCore.pyqtSignal(str)

    def __init__(self, identifier=None, state=None):
        """Create a new dataset matrix element

        Specify either an existing Dataslot identifier or a
        Dataslot state
        """
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.matrix", "dm_dataset.ui")
        uic.loadUi(path_ui, self)

        # options button
        menu = QtWidgets.QMenu()
        menu.addAction('insert anew', self.action_insert_anew)
        menu.addAction('duplicate', self.action_duplicate)
        menu.addAction('remove', self.action_remove)
        self.toolButton_opt.setMenu(menu)

        # toggle all active, all inactive, semi state
        self.toolButton_toggle.clicked.connect(self.active_toggled.emit)

        # toggle enabled/disabled state
        self.checkBox.clicked.connect(self.enabled_toggled.emit)

        # modify slot button
        self.toolButton_modify.clicked.connect(self.on_modify)

        # reduce font size of name
        font = self.label.font()
        font.setPointSize(font.pointSize()-2)
        self.label.setFont(font)

        if state is None:
            slot = pipeline.Dataslot._instances[identifier]
            self.identifier = identifier
            self.path = slot.path
            # set tooltip/label
            self.update_content()
        else:
            self.__setstate__(state)

    def __getstate__(self):
        state = {"path": self.path,
                 "identifier": self.identifier,
                 "enabled": self.checkBox.isChecked(),
                 }
        return state

    def __setstate__(self, state):
        self.identifier = state["identifier"]
        self.path = state["path"]
        self.checkBox.setChecked(state["enabled"])
        self.update_content()

    def action_duplicate(self):
        self.option_action.emit("duplicate")

    def action_insert_anew(self):
        self.option_action.emit("insert_anew")

    def action_remove(self):
        self.option_action.emit("remove")

    def on_modify(self):
        self.modify_clicked.emit(self.identifier)

    def set_label_string(self, string):
        if self.label.fontMetrics().boundingRect(string).width() < 60:
            new_string = string
        else:
            new_string = string + "..."
            while True:
                width = self.label.fontMetrics().boundingRect(new_string).width()
                if width > 60:
                    new_string = new_string[:-4] + "..."
                else:
                    break
        self.label.setText(new_string)

    def update_content(self):
        """Reset tool tips and title"""
        if self.path is not None:
            tip = meta_tool.get_repr(self.path, append_path=True)
            self.setToolTip(tip)
            self.label.setToolTip(tip)
            slot = pipeline.Dataslot._instances[self.identifier]
            name = slot.name
            self.set_label_string(name)
