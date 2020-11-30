import pkg_resources

from PyQt5 import uic, QtCore, QtWidgets


class Preferences(QtWidgets.QDialog):
    """Implements the plotting pipeline using pyqtgraph"""
    instances = {}

    def __init__(self, parent, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent=parent, *args, **kwargs)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "preferences.ui")
        uic.loadUi(path_ui, self)
        self.settings = QtCore.QSettings()
        self.parent = parent

        #: configuration keys, corresponding widgets, and defaults
        self.config_pairs = [
            ["advanced/developer mode", self.advanced_developer_mode, 0],
            ["advanced/check pyqtgraph version",
             self.advanced_check_pyqtgraph_version, 1],
            ["dcor/api key", self.dcor_api_key, ""],
            ["dcor/servers", self.dcor_servers, ["dcor.mpl.mpg.de"]],
            ["dcor/use ssl", self.dcor_use_ssl, 1],
            ["check for updates", self.general_check_for_updates, 1],
        ]
        self.reload()

        # signals
        btn_apply = self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply)
        btn_apply.clicked.connect(self.on_apply)
        btn_ok = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        btn_ok.clicked.connect(self.on_apply)
        btn_restore = self.buttonBox.button(
            QtWidgets.QDialogButtonBox.RestoreDefaults)
        btn_restore.clicked.connect(self.on_restore)

    def reload(self):
        """Read configuration or set default parameters"""
        for key, widget, default in self.config_pairs:
            value = self.settings.value(key, default)
            if isinstance(widget, QtWidgets.QCheckBox):
                widget.setChecked(bool(int(value)))
            elif isinstance(widget, QtWidgets.QLineEdit):
                widget.setText(value)
            elif widget is self.dcor_servers:
                self.dcor_servers.clear()
                self.dcor_servers.addItems(value)
                self.dcor_servers.setCurrentIndex(0)
            else:
                raise NotImplementedError("No rule for '{}'".format(key))

        # peculiarities of developer mode
        devmode = bool(int(self.settings.value("advanced/developer mode", 0)))
        self.dcor_use_ssl.setVisible(devmode)  # show "use ssl" in dev mode

    @QtCore.pyqtSlot()
    def on_apply(self):
        """Save current changes made in UI to settings and reload UI"""
        for key, widget, default in self.config_pairs:
            if isinstance(widget, QtWidgets.QCheckBox):
                value = int(widget.isChecked())
            elif isinstance(widget, QtWidgets.QLineEdit):
                value = widget.text().strip()
            elif widget is self.dcor_servers:
                curtext = self.dcor_servers.currentText()
                items = self.settings.value(key, default)
                if curtext in items:
                    items.remove(curtext)
                items.insert(0, curtext)
                value = items
            else:
                raise NotImplementedError("No rule for '{}'".format(key))
            self.settings.setValue(key, value)

        # reload UI to give visual feedback
        self.reload()

    @QtCore.pyqtSlot()
    def on_restore(self):
        self.settings.clear()
        self.reload()

    @QtCore.pyqtSlot(bool)
    def on_boolean(self, b):
        widget = self.sender()
        key = self.get_key_from_widget(widget)
        self.settings.setValue(key, int(b))
        if widget == self.advanced_developer_mode:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setText("Please restart Shape-Out for the changes to take "
                        + "effect.")
            msg.setWindowTitle("Restart Shape-Out")
            msg.exec_()
