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

from . import analysis
from . import compute
from . import export
from .matrix import BlockMatrix
from . import pipeline_plot
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
    plots_changed = QtCore.pyqtSignal()

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        path_ui = pkg_resources.resource_filename("shapeout2.gui", "main.ui")
        uic.loadUi(path_ui, self)
        #: Shape-Out settings
        self.settings = settings.SettingsFile()
        #: Analysis pipeline
        self.pipeline = pipeline.Pipeline()
        # GUI
        self.setWindowTitle("Shape-Out {}".format(__version__))
        # Disable native menubar (e.g. on Mac)
        self.menubar.setNativeMenuBar(False)
        # File menu
        self.actionQuit.triggered.connect(self.on_action_quit)
        # Help menu
        self.actionDocumentation.triggered.connect(self.on_action_docs)
        self.actionSoftware.triggered.connect(self.on_action_software)
        self.actionAbout.triggered.connect(self.on_action_about)
        # Export menu
        self.actionExportData.triggered.connect(self.on_action_export_data)
        self.actionExportFilter.triggered.connect(self.on_action_export_filter)
        self.actionExportPlot.triggered.connect(self.on_action_export_plot)
        # Comput menu
        self.actionComputeStatistics.triggered.connect(
            self.on_action_compute_statistics)
        # Initially hide buttons
        self.pushButton_preset_load.hide()
        self.pushButton_preset_save.hide()
        # Subwindows
        self.subwindows = {}
        # Subwindows for plots
        self.subwindows_plots = {}
        # Initialize a few thigns
        self.init_quick_view()
        self.init_analysis_view()
        self.mdiArea.cascadeSubWindows()
        self.showMaximized()
        # ACTIONS
        self.actionLoadDataset.triggered.connect(self.add_dataslot)
        self.actionNewFilter.triggered.connect(self.add_filter)
        self.actionNewPlot.triggered.connect(self.add_plot)
        self.toolButton_new_plot.setEnabled(False)
        self.toolButton_new_plot2.setEnabled(False)
        # BLOCK MATRIX
        # BlockMatrix wraps DataMatrix and PlotMatrix
        self.block_matrix = BlockMatrix(self.data_matrix, self.plot_matrix)
        # signals
        self.block_matrix.pipeline_changed.connect(self.adopt_pipeline)
        # BlockMatrix buttons
        self.toolButton_dm.clicked.connect(self.on_data_matrix)
        self.splitter.splitterMoved.connect(self.on_splitter)
        # DataMatrix
        self.data_matrix.slot_modify_clicked.connect(self.on_modify_slot)
        self.data_matrix.filter_modify_clicked.connect(self.on_modify_filter)
        # Plot matrix
        self.plot_matrix.plot_modify_clicked.connect(self.on_modify_plot)
        # ANALYSIS VIEW
        self.widget_ana_view.set_pipeline(self.pipeline)
        # filter signals
        self.widget_ana_view.filter_changed.connect(self.adopt_filter)
        self.widget_ana_view.pipeline_changed.connect(self.adopt_pipeline)
        # polygon filter creation
        self.widget_ana_view.widget_filter.request_new_polygon_filter.connect(
            self.on_new_polygon_filter)
        self.widget_quick_view.new_polygon_filter_created.connect(
            self.widget_ana_view.widget_filter.update_polygon_filters)
        # plot signals
        self.widget_ana_view.plot_changed.connect(self.adopt_plot)
        # slot signals
        self.widget_ana_view.slot_changed.connect(self.adopt_slot)

    @QtCore.pyqtSlot(dict)
    def adopt_filter(self, filt_state):
        filt_id = filt_state["identifier"]
        state = self.pipeline.__getstate__()
        for ii in range(len(state["filters"])):
            if state["filters"][ii]["identifier"] == filt_id:
                state["filters"][ii] = filt_state
                # make sure filters are enabled/disabled
                if (filt_state["filter used"]
                        and filt_id not in state["filters used"]):
                    state["filters used"].append(filt_id)
                elif (not filt_state["filter used"]
                      and filt_id in state["filters used"]):
                    state["filters used"].remove(filt_id)
                break
        else:
            raise ValueError("Filter not in pipeline: {}".format(filt_id))
        self.adopt_pipeline(state)

    @QtCore.pyqtSlot(dict)
    def adopt_pipeline(self, pipeline_state):
        # Set the new state of the pipeline
        self.pipeline.__setstate__(pipeline_state)
        # Update BlockMatrix
        if self.sender() != self.block_matrix:
            # Update BlockMatrix
            self.block_matrix.adopt_pipeline(pipeline_state)
        # Invalidate block matrix elements that do not make sense due to
        # filtering or plotting features.
        invalid_dm = []
        invalid_pm = []
        for slot_index, slot in enumerate(self.pipeline.slots):
            ds = self.pipeline.get_dataset(slot_index=slot_index,
                                           filt_index=None)
            for filt in self.pipeline.filters:
                # box filters
                for feat in filt.boxdict:
                    if feat not in ds.features:
                        invalid_dm.append((slot.identifier, filt.identifier))
                        break
                else:
                    # polygon filters
                    for pid in filt.polylist:
                        pf = dclab.PolygonFilter.get_instance_from_id(pid)
                        if (pf.axes[0] not in ds.features
                                or pf.axes[1] not in ds.features):
                            invalid_dm.append((slot.identifier,
                                               filt.identifier))
                            break
            for plot in self.pipeline.plots:
                plot_state = plot.__getstate__()
                if (plot_state["general"]["axis x"] not in ds
                        or plot_state["general"]["axis x"] not in ds):
                    invalid_pm.append((slot.identifier, plot.identifier))
        self.block_matrix.invalidate_elements(invalid_dm, invalid_pm)
        # Update AnalysisView
        self.widget_ana_view.adopt_pipeline(pipeline_state)
        # Update QuickView choices
        self.widget_quick_view.update_feature_choices()
        # Show Plot Windows
        # create and show
        for plot_state in pipeline_state["plots"]:
            self.add_plot_window(plot_state["identifier"])
        # remove old plot subwindows
        plot_ids = [pp["identifier"] for pp in pipeline_state["plots"]]
        for plot_id in list(self.subwindows_plots.keys()):
            if plot_id not in plot_ids:
                sub = self.subwindows_plots.pop(plot_id)
                # disconnect signals
                pw = sub.children()[-1]
                self.plots_changed.disconnect(pw.update_content)
                sub.deleteLater()
        self.plots_changed.emit()
        # redraw
        self.scrollArea_block.update()
        self.mdiArea.update()
        self.subwindows["analysis_view"].update()

    @QtCore.pyqtSlot(dict)
    def adopt_plot(self, plot_state):
        plot_id = plot_state["identifier"]
        state = self.pipeline.__getstate__()
        for ii in range(len(state["plots"])):
            if state["plots"][ii]["identifier"] == plot_id:
                state["plots"][ii] = plot_state
                break
        else:
            raise ValueError("Plot not in pipeline: {}".format(plot_id))
        self.adopt_pipeline(state)

    @QtCore.pyqtSlot(dict)
    def adopt_slot(self, slot_state):
        slot_id = slot_state["identifier"]
        state = self.pipeline.__getstate__()
        for ii in range(len(state["slots"])):
            if state["slots"][ii]["identifier"] == slot_id:
                state["slots"][ii] = slot_state
                # make sure filters are enabled/disabled
                if (slot_state["slot used"]
                        and slot_id not in state["slots used"]):
                    state["slots used"].append(slot_id)
                elif (not slot_state["slot used"]
                      and slot_id in state["slots used"]):
                    state["slots used"].remove(slot_id)
                break
        else:
            raise ValueError("Slot not in pipeline: {}".format(slot_id))
        self.adopt_pipeline(state)

    def add_dataslot(self):
        """Adds a dataslot to the pipeline"""
        fnames, _ = QtWidgets.QFileDialog.getOpenFileNames(
            parent=self,
            caption="Select an RT-DC measurement",
            directory=self.settings.get_path(name="rtdc import dataset"),
            filter="RT-DC Files (*.rtdc)")

        if fnames:
            self.toolButton_new_plot.setEnabled(True)
            self.toolButton_new_plot2.setEnabled(True)

        # Create Dataslot instance and update block matrix
        for fn in fnames:
            path = pathlib.Path(fn)
            self.settings.set_path(wd=path.parent, name="rtdc import dataset")
            # add a filter if we don't have one already
            if self.pipeline.num_filters == 0:
                self.add_filter()
            slot_id = self.pipeline.add_slot(path=path)
            self.data_matrix.add_dataset(slot_id=slot_id)

        # Update box filter limits
        self.widget_ana_view.widget_filter.update_box_ranges()
        # Update dataslot in analysis view
        self.widget_ana_view.widget_slot.update_content()
        # redraw
        self.scrollArea_block.update()

    def add_filter(self):
        filt_id = self.pipeline.add_filter()
        self.data_matrix.add_filter(identifier=filt_id)
        self.widget_ana_view.widget_filter.update_content()
        # redraw
        self.scrollArea_block.update()

    def add_plot(self):
        plot_id = self.pipeline.add_plot()
        self.plot_matrix.add_plot(identifier=plot_id)
        self.add_plot_window(plot_id)
        # update UI contents
        self.widget_ana_view.widget_plot.update_content()
        # redraw
        self.scrollArea_block.update()

    def add_plot_window(self, plot_id):
        """Create a plot window if necessary and show it"""
        if plot_id in self.subwindows_plots:
            sub = self.subwindows_plots[plot_id]
        else:
            # create subwindow
            sub = QtWidgets.QMdiSubWindow(self)
            pw = pipeline_plot.PipelinePlot(parent=sub,
                                            pipeline=self.pipeline,
                                            plot_id=plot_id)
            self.plots_changed.connect(pw.update_content)
            pw.update_content()
            sub.setSystemMenu(None)
            sub.setWindowFlags(QtCore.Qt.CustomizeWindowHint
                               | QtCore.Qt.WindowTitleHint
                               | QtCore.Qt.Tool)
            sub.setWidget(pw)
            self.mdiArea.addSubWindow(sub)
            self.subwindows_plots[plot_id] = sub
        sub.show()

    def init_analysis_view(self):
        sub = QtWidgets.QMdiSubWindow(self)
        sub.hide()
        self.widget_ana_view = analysis.AnalysisView()
        sub.setSystemMenu(None)
        sub.setWindowFlags(QtCore.Qt.CustomizeWindowHint
                           | QtCore.Qt.WindowTitleHint
                           | QtCore.Qt.Tool)
        sub.setWidget(self.widget_ana_view)
        self.mdiArea.addSubWindow(sub)
        self.toolButton_ana_view.clicked.connect(sub.setVisible)
        # applying a new filter triggers updating QuickView
        self.widget_ana_view.widget_filter.pushButton_apply.clicked.connect(
            self.on_quickview_refresh)
        self.subwindows["analysis_view"] = sub

    def init_quick_view(self):
        sub = QtWidgets.QMdiSubWindow(self)
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

    def on_action_compute_statistics(self):
        dlg = compute.ComputeStatistics(self, pipeline=self.pipeline)
        dlg.exec()

    def on_action_docs(self):
        webbrowser.open("https://shapeout2.readthedocs.io")

    def on_action_export_data(self):
        dlg = export.ExportData(self, pipeline=self.pipeline)
        if dlg.path is not None:  # user pressed cancel
            dlg.exec()

    def on_action_export_filter(self):
        dlg = export.ExportFilter(self, pipeline=self.pipeline)
        dlg.exec()

    def on_action_export_plot(self):
        dlg = export.ExportPlot(self, pipeline=self.pipeline)
        dlg.exec()

    def on_action_quit(self):
        """Determine what happens when the user wants to quit"""
        QtCore.QCoreApplication.quit()

    def on_action_software(self):
        libs = [appdirs,
                dclab,
                h5py,
                numpy,
                pg,
                scipy,
                ]
        sw_text = "Shape-Out {}\n\n".format(__version__)
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

    @QtCore.pyqtSlot()
    def on_data_matrix(self):
        """Show/hide data matrix (User clicked Data Matrix button)"""
        if self.toolButton_dm.isChecked():
            self.splitter.setSizes([200, 1000])
        else:
            self.splitter.setSizes([0, 1])
        # redraw
        self.splitter.update()
        self.mdiArea.update()
        self.scrollArea_block.update()

    def on_new_polygon_filter(self):
        if not self.pipeline.slots:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("A dataset is required for creating a polygon filter!")
            msg.setWindowTitle("No dataset loaded")
            msg.exec_()
        else:
            slot_index, _ = self.data_matrix.get_quickview_indices()
            if slot_index is None:
                # show the first dataset
                self.on_quickview_show_dataset(0, 0)
            self.on_quickview(view=True)
            self.widget_quick_view.on_poly_create()
            # adjusts QuickView size correctly
            self.widget_quick_view.on_tool()

    @QtCore.pyqtSlot(str)
    def on_modify_filter(self, filt_id):
        self.widget_ana_view.tabWidget.setCurrentIndex(2)
        self.widget_ana_view.widget_filter.show_filter(filt_id)
        # finally, check the button
        self.toolButton_ana_view.setChecked(True)
        self.subwindows["analysis_view"].setVisible(True)
        # redraw
        self.mdiArea.update()
        self.subwindows["analysis_view"].update()

    @QtCore.pyqtSlot(str)
    def on_modify_plot(self, plot_id):
        self.widget_ana_view.tabWidget.setCurrentIndex(3)
        self.widget_ana_view.widget_plot.show_plot(plot_id)
        # finally, check the button
        self.toolButton_ana_view.setChecked(True)
        self.subwindows["analysis_view"].setVisible(True)
        # redraw
        self.mdiArea.update()
        self.subwindows["analysis_view"].update()

    @QtCore.pyqtSlot(str)
    def on_modify_slot(self, slot_id):
        self.widget_ana_view.tabWidget.setCurrentIndex(1)
        self.widget_ana_view.widget_slot.show_slot(slot_id)
        # finally, check the button
        self.toolButton_ana_view.setChecked(True)
        self.subwindows["analysis_view"].setVisible(True)
        # redraw
        self.mdiArea.update()
        self.subwindows["analysis_view"].update()

    @QtCore.pyqtSlot(bool)
    def on_quickview(self, view=True):
        """Show/Hide QuickView (User clicked the QuickView button)"""
        self.subwindows["quick_view"].setVisible(view)
        self.data_matrix.enable_quickview(view)
        # redraw
        self.mdiArea.update()
        if view:
            self.subwindows["quick_view"].update()

    @QtCore.pyqtSlot()
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
        slot = self.pipeline.slots[slot_index]
        # update quick view subwindow
        self.widget_quick_view.show_rtdc(ds, slot)
        # show quick view subwindow
        if not self.subwindows["quick_view"].isVisible():
            self.toolButton_quick_view.toggle()
            self.subwindows["quick_view"].setVisible(True)
        # update FilterPanel
        filt_id = self.pipeline.filters[filt_index].identifier
        self.widget_ana_view.widget_filter.show_filter(filt_id=filt_id)

    @QtCore.pyqtSlot()
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
