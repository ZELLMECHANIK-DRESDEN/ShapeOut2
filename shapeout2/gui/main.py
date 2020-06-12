import os
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

from PyQt5 import uic, QtCore, QtGui, QtWidgets
import pyqtgraph as pg

from . import analysis
from . import compute
from . import dcor
from . import export
from . import pipeline_plot
from . import quick_view
from . import update
from . import widgets

from .. import pipeline
from .. import session
from .. import settings


from .._version import version as __version__


# global plotting configuration parameters
pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")
pg.setConfigOption("antialias", True)
pg.setConfigOption("imageAxisOrder", "row-major")


# set Qt icon theme search path
QtGui.QIcon.setThemeSearchPaths([
    os.path.join(pkg_resources.resource_filename("shapeout2", "img"),
                 "icon-theme")])
QtGui.QIcon.setThemeName(".")


class ShapeOut2(QtWidgets.QMainWindow):
    plots_changed = QtCore.pyqtSignal()

    def __init__(self):
        """Initialize Shape-Out 2

        If you pass the "--version" command line argument, the
        application will print the version after initialization
        and exit.
        """
        QtWidgets.QMainWindow.__init__(self)
        path_ui = pkg_resources.resource_filename("shapeout2.gui", "main.ui")
        uic.loadUi(path_ui, self)
        # update check
        self._update_thread = None
        self._update_worker = None
        #: Shape-Out settings
        self.settings = settings.SettingsFile()
        # Register user-defined DCOR API Key in case the user wants to
        # open a session with private data.
        api_key = self.settings.get_string("dcor api key")
        dclab.rtdc_dataset.fmt_dcor.APIHandler.add_api_key(api_key)
        #: Analysis pipeline
        self.pipeline = pipeline.Pipeline()
        # GUI
        self.setWindowTitle("Shape-Out {}".format(__version__))
        # Disable native menubar (e.g. on Mac)
        self.menubar.setNativeMenuBar(False)
        # File menu
        self.actionClearSession.triggered.connect(self.on_action_clear)
        self.actionOpenSession.triggered.connect(self.on_action_open)
        self.actionQuit.triggered.connect(self.on_action_quit)
        self.actionSaveSession.triggered.connect(self.on_action_save)
        # Help menu
        self.actionDocumentation.triggered.connect(self.on_action_docs)
        self.actionSoftware.triggered.connect(self.on_action_software)
        # developer mode
        self.actionDeveloperMode.setChecked(
            self.settings.get_bool("developer mode"))
        self.actionDeveloperMode.triggered.connect(self.on_action_develop)
        # check for updates
        do_update = self.settings.get_bool("check update")
        self.actionCheckUpdate.setChecked(do_update)
        self.actionCheckUpdate.triggered.connect(self.on_action_check_update)
        self.on_action_check_update(do_update)  # check for updates if True
        self.actionAbout.triggered.connect(self.on_action_about)
        # Export menu
        self.actionExportData.triggered.connect(self.on_action_export_data)
        self.actionExportFilter.triggered.connect(self.on_action_export_filter)
        self.actionExportPlot.triggered.connect(self.on_action_export_plot)
        # Import menu
        self.actionImportFilter.triggered.connect(self.on_action_import_filter)
        # Compute menu
        self.actionComputeStatistics.triggered.connect(
            self.on_action_compute_statistics)
        # Initially hide buttons
        self.pushButton_preset_load.hide()
        self.pushButton_preset_save.hide()
        # Subwindows
        self.subwindows = {}
        # Subwindows for plots
        self.subwindows_plots = {}
        # Initialize a few things
        self.init_quick_view()
        self.init_analysis_view()
        self.mdiArea.cascadeSubWindows()
        self.showMaximized()
        # DCOR Dialog
        self.actionLoadDCOR.triggered.connect(self.on_action_dcor)
        # BLOCK MATRIX (wraps DataMatrix and PlotMatrix)
        # BlockMatrix appearance
        self.toolButton_dm.clicked.connect(self.on_data_matrix)
        self.splitter.splitterMoved.connect(self.on_splitter)
        # BlockMatrix Actions
        self.actionLoadDataset.triggered.connect(self.add_dataslot)
        self.actionNewFilter.triggered.connect(self.add_filter)
        self.actionNewPlot.triggered.connect(self.add_plot)
        self.block_matrix.toolButton_load_dataset.clicked.connect(
            self.add_dataslot)
        self.block_matrix.toolButton_new_filter.clicked.connect(
            self.add_filter)
        self.block_matrix.toolButton_new_plot.clicked.connect(self.add_plot)
        # BlockMatrix default state
        self.toolButton_new_plot.setEnabled(False)
        self.block_matrix.toolButton_new_plot.setEnabled(False)
        # BlockMatrix other signals
        self.block_matrix.pipeline_changed.connect(self.adopt_pipeline)
        self.block_matrix.slot_modify_clicked.connect(self.on_modify_slot)
        self.block_matrix.filter_modify_clicked.connect(self.on_modify_filter)
        self.block_matrix.plot_modify_clicked.connect(self.on_modify_plot)
        # ANALYSIS VIEW
        self.widget_ana_view.set_pipeline(self.pipeline)
        # filter signals
        self.widget_ana_view.filter_changed.connect(self.adopt_filter)
        self.widget_ana_view.pipeline_changed.connect(self.adopt_pipeline)
        # polygon filter creation
        self.widget_ana_view.widget_filter.request_new_polygon_filter.connect(
            self.on_new_polygon_filter)
        self.widget_quick_view.polygon_filter_created.connect(
            self.widget_ana_view.widget_filter.update_polygon_filters)
        self.widget_quick_view.polygon_filter_modified.connect(
            self.widget_ana_view.widget_filter.update_polygon_filters)
        self.widget_quick_view.polygon_filter_modified.connect(
            self.on_quickview_refresh)  # might be an active filter (#26)
        self.widget_quick_view.polygon_filter_modified.connect(
            self.plots_changed)  # might be an active filter (#26)
        # This is important, because if meta data such as emodulus recipe
        # is changed, the QuickView must be updated as well.
        self.plots_changed.connect(self.widget_quick_view.plot)
        # plot signals
        self.widget_ana_view.plot_changed.connect(self.adopt_plot)
        # slot signals
        self.widget_ana_view.slot_changed.connect(self.adopt_slot)
        # check pyqtgraph version
        self._check_pg_version()
        # if "--version" was specified, print the version and exit
        if "--version" in sys.argv:
            print(__version__)
            QtWidgets.QApplication.processEvents()
            sys.exit(0)

    def _check_pg_version(self):
        """Tells the user if the pyqtgraph version is not correct"""
        if (self.settings.get_bool("check pgversion")
                and pg.__version__ != "0.11.0.dev0+g1c63ae5"):
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setText("You are using an unexpected version of pyqtgraph. "
                        + "Plot export may not work correctly!")
            msg.setWindowTitle("pyqtgraph version mismatch")
            msg.setDetailedText(
                "If you have installed Shape-Out using pip, please "
                + "install our pyqtgraph fork using: \n\n"
                + "pip install "
                + "git+git://github.com/ZELLMECHANIK-DRESDEN/pyqtgraph.git"
            )
            msg.exec_()

    @widgets.show_wait_cursor
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

    @widgets.show_wait_cursor
    @QtCore.pyqtSlot(dict)
    def adopt_pipeline(self, pipeline_state):
        # If the number of subplots within a plot changed, update the
        # plot size accordingly.
        for plot_index, plot_id in enumerate(self.pipeline.plot_ids):
            old_ncol, old_nrow = self.pipeline.get_plot_col_row_count(plot_id)
            try:
                new_ncol, new_nrow = self.pipeline.get_plot_col_row_count(
                    plot_id, pipeline_state)
                lay = pipeline_state["plots"][plot_index]["layout"]
            except (KeyError, IndexError):
                # the plot was removed
                continue
            else:
                lay["size x"] += 200*(new_ncol-old_ncol)
                lay["size y"] += 200*(new_nrow-old_nrow)
        # set the new state of the pipeline
        self.pipeline.__setstate__(pipeline_state)
        # update BlockMatrix
        if self.sender() != self.block_matrix:
            # Update BlockMatrix
            self.block_matrix.adopt_pipeline(pipeline_state)
        # trigger redraw
        self.block_matrix.update()
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
        # update list of polygon filters in Quick View
        self.widget_quick_view.update_polygon_panel()
        # Show Plot Windows
        # create and show
        for plot_state in pipeline_state["plots"]:
            self.add_plot_window(plot_state["identifier"])
        # remove old plot subwindows
        plot_ids = [pp["identifier"] for pp in pipeline_state["plots"]]
        for plot_id in list(self.subwindows_plots.keys()):
            if plot_id not in plot_ids:
                sub = self.subwindows_plots.pop(plot_id)
                for child in sub.children():
                    # disconnect signals
                    if isinstance(child, pipeline_plot.PipelinePlot):
                        self.plots_changed.disconnect(child.update_content)
                        break
                sub.deleteLater()
        self.plots_changed.emit()
        self.widget_ana_view.widget_plot.update_content()
        # Remove zombie slots
        for slot_id in list(pipeline.Dataslot._instances.keys()):
            if slot_id not in self.pipeline.slot_ids:
                pipeline.Dataslot.remove_slot(slot_id)
        # enable buttons
        if self.pipeline.slots:
            self.toolButton_new_plot.setEnabled(True)
            self.block_matrix.toolButton_new_plot.setEnabled(True)
        else:
            self.toolButton_new_plot.setEnabled(False)
            self.block_matrix.toolButton_new_plot.setEnabled(False)
        # redraw
        self.block_matrix.update()
        self.mdiArea.update()
        self.subwindows["analysis_view"].update()

    @widgets.show_wait_cursor
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

    @widgets.show_wait_cursor
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

    @widgets.show_wait_cursor
    @QtCore.pyqtSlot()
    def add_dataslot(self, paths=None, is_dcor=False):
        """Adds a dataslot to the pipeline

        Parameters
        ----------
        paths: list of str or None
            If specified, no file dialog is displayed and the files
            specified are loaded. Can also be DCOR URL.
        is_dcor: bool
            If set to True, `paths` will be treated as a list of
            DCOR URLs. Does not have any effect if `paths` is None.
        """
        if paths is None:
            fnames, _ = QtWidgets.QFileDialog.getOpenFileNames(
                parent=self,
                caption="Select an RT-DC measurement",
                directory=self.settings.get_path(name="rtdc import dataset"),
                filter="RT-DC Files (*.rtdc)")
        else:
            fnames = paths

        if fnames:
            self.toolButton_new_plot.setEnabled(True)
            self.block_matrix.toolButton_new_plot.setEnabled(True)

        slot_ids = []
        # Create Dataslot instance and update block matrix
        for fn in fnames:
            if is_dcor:
                path = fn
            else:
                path = pathlib.Path(fn)
                self.settings.set_path(wd=path.parent,
                                       name="rtdc import dataset")
            # add a filter if we don't have one already
            if self.pipeline.num_filters == 0:
                self.add_filter()
            slot_id = self.pipeline.add_slot(path=path)
            self.block_matrix.add_dataset(slot_id=slot_id)
            slot_ids.append(slot_id)

        # Update box filter limits
        self.widget_ana_view.widget_filter.update_box_ranges()
        # Update dataslot in analysis view
        self.widget_ana_view.widget_slot.update_content()
        # redraw
        self.block_matrix.update()
        return slot_ids

    def add_filter(self):
        """Add a filter using tool buttons"""
        filt_id = self.pipeline.add_filter()
        self.block_matrix.add_filter(identifier=filt_id)
        self.widget_ana_view.widget_filter.update_content()
        # redraw
        self.block_matrix.update()
        return filt_id

    def add_plot(self):
        plot_id = self.pipeline.add_plot()
        self.block_matrix.add_plot(identifier=plot_id)
        self.add_plot_window(plot_id)
        # update UI contents
        self.widget_ana_view.widget_plot.update_content()
        # redraw
        self.block_matrix.update()
        return plot_id

    def add_plot_window(self, plot_id):
        """Create a plot window if necessary and show it"""
        if plot_id in self.subwindows_plots:
            sub = self.subwindows_plots[plot_id]
        else:
            # create subwindow
            sub = widgets.MDISubWindowWOButtons(self)
            pw = pipeline_plot.PipelinePlot(parent=sub,
                                            pipeline=self.pipeline,
                                            plot_id=plot_id)
            self.plots_changed.connect(pw.update_content)
            pw.update_content()
            sub.setWidget(pw)
            self.mdiArea.addSubWindow(sub)
            self.subwindows_plots[plot_id] = sub
            sub.setFixedSize(sub.sizeHint())
        sub.show()

    def dragEnterEvent(self, e):
        """Whether files are accepted"""
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        """Add dropped files to view"""
        urls = e.mimeData().urls()
        pathlist = []
        for ff in urls:
            pp = pathlib.Path(ff.toLocalFile())
            if pp.is_dir():
                pathlist += list(pp.rglob("*.rtdc"))
            elif pp.suffix == ".rtdc":
                pathlist.append(pp)
        if pathlist:
            self.add_dataslot(paths=sorted(pathlist))

    def init_analysis_view(self):
        sub = widgets.MDISubWindowWOButtons(self)
        self.widget_ana_view = analysis.AnalysisView()
        self.subwindows["analysis_view"] = sub
        sub.setWidget(self.widget_ana_view)
        sub.hide()
        self.mdiArea.addSubWindow(sub)
        self.toolButton_ana_view.clicked.connect(sub.setVisible)
        # applying a new filter triggers updating QuickView
        self.widget_ana_view.widget_filter.pushButton_apply.clicked.connect(
            self.on_quickview_refresh)

    def init_quick_view(self):
        sub = widgets.MDISubWindowWOButtons(self)
        self.widget_quick_view = quick_view.QuickView()
        sub.setWidget(self.widget_quick_view)
        self.toolButton_quick_view.clicked.connect(self.on_quickview)
        self.subwindows["quick_view"] = sub
        # signals
        self.block_matrix.quickviewed.connect(self.on_quickview_show_dataset)
        sub.hide()
        self.mdiArea.addSubWindow(sub)

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

    @QtCore.pyqtSlot(bool)
    def on_action_check_update(self, b):
        self.settings.set_bool("check update", b)
        if b and self._update_thread is None:
            self._update_thread = QtCore.QThread()
            self._update_worker = update.UpdateWorker()
            self._update_worker.moveToThread(self._update_thread)
            self._update_worker.finished.connect(self._update_thread.quit)
            self._update_worker.data_ready.connect(
                self.on_action_check_update_finished)
            self._update_thread.start()

            version = __version__
            ghrepo = "ZELLMECHANIK-DRESDEN/ShapeOut2"

            QtCore.QMetaObject.invokeMethod(self._update_worker,
                                            'processUpdate',
                                            QtCore.Qt.QueuedConnection,
                                            QtCore.Q_ARG(str, version),
                                            QtCore.Q_ARG(str, ghrepo),
                                            )

    @QtCore.pyqtSlot(dict)
    def on_action_check_update_finished(self, mdict):
        # cleanup
        self._update_thread.quit()
        self._update_thread.wait()
        self._update_worker = None
        self._update_thread = None
        # display message box
        ver = mdict["version"]
        web = mdict["releases url"]
        dlb = mdict["binary url"]
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Shape-Out {} available!".format(ver))
        msg.setTextFormat(QtCore.Qt.RichText)
        text = "You can install Shape-Out {} ".format(ver)
        if dlb is not None:
            text += 'from a <a href="{}">direct download</a>. '.format(dlb)
        else:
            text += 'by running `pip install --upgrade shapeout2`. '
        text += 'Visit the <a href="{}">official release page</a>!'.format(web)
        msg.setText(text)
        msg.exec_()

    def on_action_compute_statistics(self):
        dlg = compute.ComputeStatistics(self, pipeline=self.pipeline)
        dlg.exec()

    @QtCore.pyqtSlot(bool)
    def on_action_develop(self, b):
        self.settings.set_bool("developer mode", b)
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Please restart Shape-Out for the changes to take effect.")
        msg.setWindowTitle("Restart Shape-Out")
        msg.exec_()

    @QtCore.pyqtSlot()
    def on_action_clear(self, assume_yes=False):
        if assume_yes:
            yes = True
        else:
            buttonReply = QtWidgets.QMessageBox.question(
                self, 'Clear Session', "All progress will be lost. Continue?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No)
            yes = buttonReply == QtWidgets.QMessageBox.Yes
        if yes:
            session.clear_session(self.pipeline)
            self.reload_pipeline()
        return yes

    def on_action_dcor(self):
        """Show the DCOR import dialog"""
        dlg = dcor.DCORLoader(self)
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

    def on_action_import_filter(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Select Filter', '', 'Filters formats (*.poly *.sof)')
        if path:
            session.import_filters(path, self.pipeline)
            # update UI
            self.reload_pipeline()

    @QtCore.pyqtSlot()
    def on_action_open(self, path=None):
        if self.pipeline.slots or self.pipeline.filters:
            if not self.on_action_clear():
                return
        if path is None:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, 'Open session', '', 'Shape-Out 2 session (*.so2)',
                'Shape-Out 2 session (*.so2)',
                QtWidgets.QFileDialog.DontUseNativeDialog)
        if path:
            search_paths = []
            while True:
                try:
                    with widgets.ShowWaitCursor():
                        session.open_session(path, self.pipeline, search_paths)
                except session.DataFileNotFoundError as e:
                    missds = "\r".join([str(pp) for pp in e.missing_paths])
                    msg = QtWidgets.QMessageBox()
                    msg.setIcon(QtWidgets.QMessageBox.Warning)
                    msg.setText("Some datasets were not found! "
                                + "Please specify a search location.")
                    msg.setWindowTitle(
                        "Missing {} dataset(s)".format(len(e.missing_paths)))
                    msg.setDetailedText("Missing files: \n\n" + missds)
                    msg.exec_()
                    spath = QtWidgets.QFileDialog.getExistingDirectory(
                        self, 'Data search path')
                    if spath:
                        search_paths.append(spath)
                    else:
                        break
                else:
                    break
            self.reload_pipeline()

    def on_action_quit(self):
        """Determine what happens when the user wants to quit"""
        if self.pipeline.slots or self.pipeline.filters:
            if not self.on_action_clear():
                return
        QtCore.QCoreApplication.quit()

    def on_action_save(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save session', '', 'Shape-Out 2 session (*.so2)')
        if path:
            if not path.endswith(".so2"):
                path += ".so2"
            session.save_session(path, self.pipeline)

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
        sw_text += "\n Breeze icon theme by the KDE Community (LGPL)."
        if hasattr(sys, 'frozen'):
            sw_text += "\nThis executable has been created using PyInstaller."
        QtWidgets.QMessageBox.information(self,
                                          "Software",
                                          sw_text)

    @widgets.show_wait_cursor
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
        self.block_matrix.update()

    def on_new_polygon_filter(self):
        if not self.pipeline.slots:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("A dataset is required for creating a polygon filter!")
            msg.setWindowTitle("No dataset loaded")
            msg.exec_()
        else:
            slot_index, _ = self.block_matrix.get_quickview_indices()
            if slot_index is None:
                # show the first dataset
                self.on_quickview_show_dataset(0, 0)
            self.on_quickview(view=True)
            self.widget_quick_view.on_poly_create()
            # adjusts QuickView size correctly
            self.widget_quick_view.on_tool()

    @widgets.show_wait_cursor
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

    @widgets.show_wait_cursor
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

    @widgets.show_wait_cursor
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

    @widgets.show_wait_cursor
    @QtCore.pyqtSlot(bool)
    def on_quickview(self, view=True):
        """Show/Hide QuickView (User clicked the QuickView button)"""
        self.subwindows["quick_view"].setVisible(view)
        self.block_matrix.enable_quickview(view)
        # redraw
        self.mdiArea.update()
        if view:
            self.subwindows["quick_view"].update()

    @widgets.show_wait_cursor
    @QtCore.pyqtSlot()
    def on_quickview_refresh(self):
        """Refresh quickview with the currently shown dataset"""
        slot_index, filt_index = self.block_matrix.get_quickview_indices()
        if slot_index is not None:
            self.on_quickview_show_dataset(slot_index, filt_index,
                                           update_ana_filter=False)

    @widgets.show_wait_cursor
    @QtCore.pyqtSlot(int, int)
    def on_quickview_show_dataset(self, slot_index, filt_index,
                                  update_ana_filter=True):
        """Update QuickView dataset (User selected new dataset)

        Parameters
        ----------
        slot_index: int
            Index of the slot in `self.pipeline`
        filt_index: int
            Index of the filter in `self.pipeline`
        update_ana_filter: bool
            Whether to update the filter panel in the analysis view.
            If True, matches the filter displayed in the panel to
            the one where QuickView is currently set active. If
            False, nothing is changed.
        """
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
        if update_ana_filter:
            # update FilterPanel
            filt_id = self.pipeline.filters[filt_index].identifier
            self.widget_ana_view.widget_filter.show_filter(filt_id=filt_id)

    @QtCore.pyqtSlot()
    def on_splitter(self):
        if self.splitter.sizes()[0] == 0:
            self.toolButton_dm.setChecked(False)
        else:
            self.toolButton_dm.setChecked(True)

    def reload_pipeline(self):
        """Convenience function for reloading the current pipeline"""
        self.adopt_pipeline(self.pipeline.__getstate__())


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
    errorbox.setIcon(QtWidgets.QMessageBox.Critical)
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
