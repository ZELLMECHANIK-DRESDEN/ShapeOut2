import pathlib
import pkg_resources
import platform

from dclab.lme4.rlibs import rpy2, MockRPackage
from dclab.lme4 import rsetup
from PyQt5 import uic, QtCore, QtWidgets

from .widgets import show_wait_cursor

RPY2_AVAILABLE = not isinstance(rpy2, MockRPackage)


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

        # Get default R path
        if RPY2_AVAILABLE and rsetup.has_r():
            rdefault = rsetup.get_r_path()
        else:
            rdefault = ""

        # disable R settings
        self.tab_r.setEnabled(RPY2_AVAILABLE)

        #: configuration keys, corresponding widgets, and defaults
        self.config_pairs = [
            ["advanced/developer mode", self.advanced_developer_mode, 0],
            ["check for updates", self.general_check_for_updates, 1],
            ["dcor/api key", self.dcor_api_key, ""],
            ["dcor/servers", self.dcor_servers, ["dcor.mpl.mpg.de"]],
            ["dcor/use ssl", self.dcor_use_ssl, 1],
            ["lme4/r path", self.lme4_rpath, rdefault],
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
        # lme4 buttons
        self.pushButton_lme4_install.clicked.connect(self.on_lme4_install)
        self.pushButton_lme4_search.clicked.connect(self.on_lme4_search_r)

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

        if RPY2_AVAILABLE:
            self.reload_lme4()

        # peculiarities of developer mode
        devmode = bool(int(self.settings.value("advanced/developer mode", 0)))
        self.dcor_use_ssl.setVisible(devmode)  # show "use ssl" in dev mode

    @show_wait_cursor
    def reload_lme4(self, install=False):
        """Reload information about lme4, optionally installing it"""
        # set the binary
        binary = self.lme4_rpath.text()
        if pathlib.Path(binary).is_file():
            rsetup.set_r_path(binary)
        # check lme4 package status
        if not rsetup.has_r():
            r_version = "unknown"
            lme4_st = "unknown"
        else:
            r_version = rsetup.get_r_version()
            if rsetup.has_lme4():
                lme4_st = "installed"
            else:
                lme4_st = "not installed"

        if install and lme4_st == "not installed":
            self.setEnabled(False)
            rsetup.install_lme4()
            self.setEnabled(True)
            # update interface with installed lme4
            self.reload_lme4(install=False)
        else:
            # update user interface
            self.pushButton_lme4_install.setVisible(lme4_st == "not installed")
            self.label_r_version.setText(r_version)
            self.label_lme4_installed.setText(lme4_st)

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
    def on_lme4_install(self):
        self.reload_lme4(install=True)

    @QtCore.pyqtSlot()
    def on_lme4_search_r(self):
        if platform.system() == "Windows":
            filters = "Executable (*.exe)"
        else:
            filters = ""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Executable", ".", filters)
        if path:
            self.lme4_rpath.setText(path)

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
