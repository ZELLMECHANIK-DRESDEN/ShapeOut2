import pathlib
import pkg_resources
import signal
import sys
import traceback

from PyQt5 import uic, QtCore, QtWidgets
import pyqtgraph as pg

from . import ana_view
from . import quick_view

from .. import settings
from .. import pipeline

from .._version import version as __version__


# global plotting configuration parameters
pg.setConfigOption("background", None)
pg.setConfigOption("foreground", "k")
pg.setConfigOption("antialias", False)
pg.setConfigOption("imageAxisOrder", "row-major")


class ShapeOut2(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        path_ui = pkg_resources.resource_filename("shapeout2.gui", "main.ui")
        uic.loadUi(path_ui, self)
        self.setWindowTitle("Shape-Out {}".format(__version__))
        # Disable native menubar (e.g. on Mac)
        self.menubar.setNativeMenuBar(False)
        # Initially hide buttons
        self.pushButton_preset_load.hide()
        self.pushButton_preset_save.hide()
        # Subwindows
        self.subwindows = {}
        self.init_quick_view()
        self.init_ana_view()
        self.mdiArea.cascadeSubWindows()
        self.showMaximized()
        # data matrix
        self.toolButton_dm.clicked.connect(self.on_data_matrix)
        self.splitter.splitterMoved.connect(self.on_splitter)
        self.toolButton_new_filter.clicked.connect(self.add_filter)
        self.toolButton_new_dataset.clicked.connect(self.add_dataslot)
        self.toolButton_import.clicked.connect(self.add_dataslot)
        self.toolButton_new_plot.clicked.connect(self.plot_matrix.add_plot)
        # settings
        self.settings = settings.SettingsFile()

    def add_dataslot(self):
        fnames, _ = QtWidgets.QFileDialog.getOpenFileNames(
            parent=self,
            caption="Select an RT-DC measurement",
            directory=self.settings.get_path(name="rtdc import dataset"),
            filter="RT-DC Files (*.rtdc)")

        for fn in fnames:
            path = pathlib.Path(fn)
            self.settings.set_path(wd=path.parent, name="rtdc import dataset")
            self.data_matrix.add_dataset(path)

    def add_filter(self):
        self.data_matrix.add_filter()
        self.widget_ana_view.widget_filter.update_content()

    def init_ana_view(self):
        sub = QtWidgets.QMdiSubWindow()
        sub.hide()
        self.widget_ana_view = ana_view.InfoView()
        sub.setWidget(self.widget_ana_view)
        self.mdiArea.addSubWindow(sub)
        self.toolButton_ana_view.clicked.connect(sub.setVisible)
        self.subwindows["ana_view"] = sub
        sub.setSystemMenu(None)
        sub.setWindowFlags(QtCore.Qt.CustomizeWindowHint
                           | QtCore.Qt.WindowTitleHint
                           | QtCore.Qt.Tool)

    def init_quick_view(self):
        sub = QtWidgets.QMdiSubWindow()
        sub.hide()
        self.widget_quick_view = quick_view.QuickView()
        sub.setWidget(self.widget_quick_view)
        self.mdiArea.addSubWindow(sub)
        self.toolButton_quick_view.clicked.connect(self.on_quickview)
        self.subwindows["quick_view"] = sub
        # signals
        self.data_matrix.quickviewed.connect(self.on_quickviewed)
        sub.setSystemMenu(None)
        sub.setWindowFlags(QtCore.Qt.CustomizeWindowHint
                           | QtCore.Qt.WindowTitleHint
                           | QtCore.Qt.Tool)

    def on_data_matrix(self):
        if self.toolButton_dm.isChecked():
            self.splitter.setSizes([200, 1000])
        else:
            self.splitter.setSizes([0, 1])

    @QtCore.pyqtSlot(bool)
    def on_quickview(self, view):
        if self.subwindows["quick_view"].isVisible():
            self.subwindows["quick_view"].setVisible(False)
            self.data_matrix.enable_quickview(False)
        else:
            self.subwindows["quick_view"].setVisible(True)
            self.data_matrix.enable_quickview(True)

    @QtCore.pyqtSlot(int, int)
    def on_quickviewed(self, slot_index, filt_index):
        # get state of data matrix
        state = self.data_matrix.__getstate__()
        pl = pipeline.Pipeline(state=state)
        ds = pl.get_dataset(slot_index=slot_index,
                            filt_index=filt_index,
                            apply_filter=True)
        # update quick view subwindow
        self.widget_quick_view.show_rtdc(ds)
        # show quick view subwindow
        if not self.subwindows["quick_view"].isVisible():
            self.toolButton_quick_view.toggle()
            self.subwindows["quick_view"].setVisible(True)
        # update FilterPanel
        filt_id = pl.filters[filt_index].identifier
        self.widget_ana_view.widget_filter.show_filter(filt_id=filt_id)

    def on_splitter(self):
        if self.splitter.sizes()[0] == 0:
            self.toolButton_dm.setChecked(False)
        else:
            self.toolButton_dm.setChecked(True)


def excepthook(etype, value, trace):
    """
    Handler for all unhandled exceptions.

    :param `etype`: the exception type (`SyntaxError`,
        `ZeroDivisionError`, etc...);
    :type `etype`: `Exception`
    :param string `value`: the exception error message;
    :param string `trace`: the traceback header, if any (otherwise, it
        prints the standard Python header: ``Traceback (most recent
        call last)``.
    """
    vinfo = "Unhandled exception in Shape-Out version {}:\n".format(
        __version__)
    tmp = traceback.format_exception(etype, value, trace)
    exception = "".join([vinfo]+tmp)

    errorbox = QtWidgets.QMessageBox()
    errorbox.addButton(QtWidgets.QPushButton('Close'),
                       QtWidgets.QMessageBox.YesRole)
    errorbox.addButton(QtWidgets.QPushButton(
        'Copy text && Close'), QtWidgets.QMessageBox.NoRole)
    errorbox.setText(exception)
    ret = errorbox.exec_()
    if ret == 1:
        cb = QtWidgets.QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(exception)


# Make Ctr+C close the app
signal.signal(signal.SIGINT, signal.SIG_DFL)
# Display exception hook in separate dialog instead of crashing
sys.excepthook = excepthook
