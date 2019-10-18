import pathlib
import pkg_resources
import signal
import sys
import traceback
import webbrowser

import appdirs
import dclab
import h5py
import numpy
import scipy

from PyQt5 import uic, QtCore, QtWidgets
import pyqtgraph as pg

from . import ana_view
from . import quick_view

from .. import settings
from .. import pipeline

from .._version import version as __version__


# global plotting configuration parameters
pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")
pg.setConfigOption("antialias", True)
pg.setConfigOption("imageAxisOrder", "row-major")


class ShapeOut2(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        path_ui = pkg_resources.resource_filename("shapeout2.gui", "main.ui")
        uic.loadUi(path_ui, self)
        self.setWindowTitle("Shape-Out {}".format(__version__))
        # Disable native menubar (e.g. on Mac)
        self.menubar.setNativeMenuBar(False)
        # File menu
        self.action_Quit.triggered.connect(self.on_action_quit)
        # Help menu
        self.action_Documentation.triggered.connect(self.on_action_docs)
        self.action_Software.triggered.connect(self.on_action_software)
        self.action_About.triggered.connect(self.on_action_about)
        # Initially hide buttons
        self.pushButton_preset_load.hide()
        self.pushButton_preset_save.hide()
        # Subwindows
        self.subwindows = {}
        self.init_quick_view()
        self.init_analysis_view()
        self.mdiArea.cascadeSubWindows()
        self.showMaximized()
        # data matrix
        self.data_matrix.matrix_changed.connect(self.update_pipeline)
        self.data_matrix.filter_modify_clicked.connect(
            self.on_modify_filter)
        self.widget_ana_view.widget_filter.filters_changed.connect(
            self.data_matrix.update_content)
        self.toolButton_dm.clicked.connect(self.on_data_matrix)
        self.splitter.splitterMoved.connect(self.on_splitter)
        self.toolButton_new_filter.clicked.connect(self.add_filter)
        self.toolButton_new_dataset.clicked.connect(self.add_dataslot)
        self.toolButton_import.clicked.connect(self.add_dataslot)
        self.toolButton_new_plot.clicked.connect(self.plot_matrix.add_plot)
        # analysis view
        self.widget_ana_view.widget_filter.request_box_range_update.connect(
            self.update_ana_filter_box_ranges)
        #: Shape-Out settings
        self.settings = settings.SettingsFile()
        #: Analysis pipeline
        self.pipeline = pipeline.Pipeline()

    def add_dataslot(self):
        fnames, _ = QtWidgets.QFileDialog.getOpenFileNames(
            parent=self,
            caption="Select an RT-DC measurement",
            directory=self.settings.get_path(name="rtdc import dataset"),
            filter="RT-DC Files (*.rtdc)")

        for fn in fnames:
            path = pathlib.Path(fn)
            self.settings.set_path(wd=path.parent, name="rtdc import dataset")
            # add a filter if we don't have one already
            if self.pipeline.num_filters == 0:
                self.add_filter()
            slot_id = self.pipeline.add_slot(path=path)
            self.data_matrix.add_dataset(identifier=slot_id)

        # Update box filter limits
        self.update_ana_filter_box_ranges()

    def add_filter(self):
        filt_id = self.pipeline.add_filter()
        self.data_matrix.add_filter(identifier=filt_id)
        self.widget_ana_view.widget_filter.update_content()

    def init_analysis_view(self):
        sub = QtWidgets.QMdiSubWindow()
        sub.hide()
        self.widget_ana_view = ana_view.AnalysisView()
        sub.setWidget(self.widget_ana_view)
        self.mdiArea.addSubWindow(sub)
        self.toolButton_ana_view.clicked.connect(sub.setVisible)
        self.widget_ana_view.widget_filter.pushButton_update.clicked.connect(
            self.on_quickview_refresh)
        self.subwindows["analysis_view"] = sub
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
        self.data_matrix.quickviewed.connect(self.on_quickview_show_dataset)
        sub.setSystemMenu(None)
        sub.setWindowFlags(QtCore.Qt.CustomizeWindowHint
                           | QtCore.Qt.WindowTitleHint
                           | QtCore.Qt.Tool)

    def on_action_docs(self):
        webbrowser.open("https://shapeout2.readthedocs.io")

    def on_action_quit(self):
        """Determine what happens when the user wants to quit"""
        QtCore.QCoreApplication.quit()

    def on_action_about(self):
        about_text = "Shape-Out 2 is the successor of Shape-Out, " \
            + "a graphical user interface for the analysis and " \
            + "visualization of RT-DC data sets.\n\n" \
            + "Author: Paul Müller\n" \
            + "Code: https://github.com/ZELLMECHANIK-DRESDEN/ShapeOut2\n" \
            + "Documentation: https://shapeout2.readthedocs.io"
        QtWidgets.QMessageBox.about(self,
                                    "Shape-Out {}".format(__version__),
                                    about_text)

    def on_action_software(self):
        libs = [appdirs,
                dclab,
                h5py,
                numpy,
                pg,
                scipy,
                ]
        sw_text = "PyJibe {}\n\n".format(__version__)
        sw_text += "Python {}\n\n".format(sys.version)
        sw_text += "Modules:\n"
        for lib in libs:
            sw_text += "- {} {}\n".format(lib.__name__, lib.__version__)
        sw_text += "- PyQt5 {}\n".format(QtCore.QT_VERSION_STR)
        if hasattr(sys, 'frozen'):
            sw_text += "\nThis executable has been created using PyInstaller."
        QtWidgets.QMessageBox.information(self,
                                          "Software",
                                          sw_text)

    def on_data_matrix(self):
        """Show/hide data matrix (User clicked Data Matrix button)"""
        if self.toolButton_dm.isChecked():
            self.splitter.setSizes([200, 1000])
        else:
            self.splitter.setSizes([0, 1])

    @QtCore.pyqtSlot(str)
    def on_modify_filter(self, filt_id):
        self.widget_ana_view.tabWidget.setCurrentIndex(1)
        self.widget_ana_view.widget_filter.show_filter(filt_id)
        # finally, check the button
        self.toolButton_ana_view.setChecked(True)
        self.subwindows["analysis_view"].setVisible(True)

    @QtCore.pyqtSlot(bool)
    def on_quickview(self, view=True):
        """Show/Hide QuickView (User clicked the QuickView button)"""
        self.subwindows["quick_view"].setVisible(view)
        self.data_matrix.enable_quickview(view)

    def on_quickview_refresh(self):
        """Refresh quickview with the currently shown dataset"""
        slot_index, filt_index = self.data_matrix.get_quickview_indices()
        if slot_index is not None:
            self.on_quickview_show_dataset(slot_index, filt_index)

    @QtCore.pyqtSlot(int, int)
    def on_quickview_show_dataset(self, slot_index, filt_index):
        """Update QuickView dataset (User selected new dataset)"""
        ds = self.pipeline.get_dataset(slot_index=slot_index,
                                       filt_index=filt_index,
                                       apply_filter=True)
        # update quick view subwindow
        self.widget_quick_view.show_rtdc(ds)
        # show quick view subwindow
        if not self.subwindows["quick_view"].isVisible():
            self.toolButton_quick_view.toggle()
            self.subwindows["quick_view"].setVisible(True)
        # update FilterPanel
        filt_id = self.pipeline.filters[filt_index].identifier
        self.widget_ana_view.widget_filter.show_filter(filt_id=filt_id)

    def on_splitter(self):
        if self.splitter.sizes()[0] == 0:
            self.toolButton_dm.setChecked(False)
        else:
            self.toolButton_dm.setChecked(True)

    @QtCore.pyqtSlot()
    def update_ana_filter_box_ranges(self):
        """Update the ranges and limits of the box filters"""
        # get the currently used box filter names
        features = self.widget_ana_view.widget_filter.active_box_features
        # compute min/max values
        mmdict = {}
        for feat in features:
            mmdict[feat] = self.pipeline.get_min_max(feat=feat)
        # apply to box filters
        self.widget_ana_view.widget_filter.update_box_filters(mmdict)

    @QtCore.pyqtSlot(dict)
    def update_pipeline(self, state):
        self.pipeline.__setstate__(state)


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
