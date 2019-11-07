import pathlib
import pkg_resources

import dclab
import numpy as np
from PyQt5 import uic, QtCore, QtWidgets
import pyqtgraph as pg
from scipy.ndimage import binary_erosion

from .. import plot_cache

from . import idiom
from . import pipeline_plot


class QuickView(QtWidgets.QWidget):
    new_polygon_filter_created = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "quick_view.ui")
        uic.loadUi(path_ui, self)
        path_css = pkg_resources.resource_filename(
            "shapeout2.gui", "quick_view.css")
        stylesheet = pathlib.Path(path_css).read_text()
        self.groupBox_image.setStyleSheet(stylesheet)
        self.groupBox_trace.setStyleSheet(stylesheet)

        self.setWindowTitle("Quick View (QV)")

        # Initially, only show the info about how QuickView works
        self.widget_tool.setEnabled(False)
        self.widget_scatter.hide()

        # Set scale options (with data)
        for cb in [self.comboBox_xscale, self.comboBox_yscale]:
            cb.clear()
            cb.addItem("linear", "linear")
            cb.addItem("logarithmic", "log")

        # Hide settings/events by default
        self.widget_event.setVisible(False)
        self.widget_settings.setVisible(False)
        self.widget_poly.setVisible(False)

        # settings button
        self.toolButton_event.toggled.connect(self.on_tool)
        self.toolButton_poly.toggled.connect(self.on_tool)
        self.toolButton_settings.toggled.connect(self.on_tool)

        # polygon filter signals
        self.label_poly_create.hide()
        self.label_poly_modify.hide()
        self.pushButton_poly_save.hide()
        self.pushButton_poly_cancel.hide()
        self.pushButton_poly_create.clicked.connect(self.on_poly_create)
        self.pushButton_poly_save.clicked.connect(self.on_poly_done)
        self.pushButton_poly_cancel.clicked.connect(self.on_poly_done)
        self.comboBox_poly.currentIndexChanged.connect(self.on_poly_modify)
        self.update_polygon_panel()

        # event changed signal
        self.widget_scatter.scatter.sigClicked.connect(
            self.on_event_scatter_clicked)
        self.spinBox_event.valueChanged.connect(self.on_event_scatter_spin)
        self.checkBox_image_contour.stateChanged.connect(
            self.on_event_scatter_update)
        self.checkBox_image_contrast.stateChanged.connect(
            self.on_event_scatter_update)
        self.checkBox_image_zoom.stateChanged.connect(
            self.on_event_scatter_update)
        self.checkBox_trace_raw.stateChanged.connect(
            self.on_event_scatter_update)
        self.checkBox_trace_zoom.stateChanged.connect(
            self.on_event_scatter_update)

        # value changed signals for plot
        self.signal_widgets = [self.checkBox_downsample,
                               self.spinBox_downsample,
                               self.comboBox_x,
                               self.comboBox_y,
                               self.comboBox_xscale,
                               self.comboBox_yscale,
                               self.checkBox_isoelastics,
                               ]
        for w in self.signal_widgets:
            if hasattr(w, "currentIndexChanged"):
                w.currentIndexChanged.connect(self.plot)
            elif hasattr(w, "stateChanged"):
                w.stateChanged.connect(self.plot)
            elif hasattr(w, "valueChanged"):
                w.valueChanged.connect(self.plot)

        # disable pyqtgraph controls we don't need
        for vim in [self.imageView_image]:
            vim.ui.histogram.hide()
            vim.ui.roiBtn.hide()
            vim.ui.menuBtn.hide()
            # disable keyboard shortcuts
            vim.keyPressEvent = lambda _: None
            vim.keyReleaseEvent = lambda _: None
        # Defaults for trace plot
        self.graphicsView_trace.setBackground('w')
        # General plot options
        # show top and right axes, but not ticklabels
        for kax in ["top", "right"]:
            self.graphicsView_trace.plotItem.showAxis(kax)
            ax = self.graphicsView_trace.plotItem.axes[kax]["item"]
            ax.setTicks([])
        # show grid
        self.graphicsView_trace.plotItem.showGrid(x=True, y=True, alpha=.1)

        # Set individual plots
        kw0 = dict(x=np.arange(10), y=np.arange(10))
        self.trace_plots = {
            "fl1_raw": pg.PlotDataItem(pen="#6EA068", **kw0),  # green
            "fl2_raw": pg.PlotDataItem(pen="#8E7A45", **kw0),  # orange
            "fl3_raw": pg.PlotDataItem(pen="#8F4D48", **kw0),  # red
            "fl1_median": pg.PlotDataItem(pen="#15BF00", **kw0),  # green
            "fl2_median": pg.PlotDataItem(pen="#BF8A00", **kw0),  # orange
            "fl3_median": pg.PlotDataItem(pen="#BF0C00", **kw0),  # red
        }
        for key in self.trace_plots:
            self.graphicsView_trace.addItem(self.trace_plots[key])
            self.trace_plots[key].hide()

        self.graphicsView_trace.plotItem.setLabels(
            left="Fluorescence [a.u.]", bottom="Event time [µs]")

        #: default parameters for the event image
        self.imkw = dict(autoLevels=False,
                         levels=(0, 254),
                         )

    def __getstate__(self):
        plot = {
            "downsampling": self.checkBox_downsample.isChecked(),
            "downsampling value": self.spinBox_downsample.value(),
            "axis x": self.comboBox_x.currentData(),
            "axis y": self.comboBox_y.currentData(),
            "scale x": self.comboBox_xscale.currentData(),
            "scale y": self.comboBox_yscale.currentData(),
            "isoelastics": self.checkBox_isoelastics.isChecked(),
        }
        event = {
            "index": self.spinBox_event.value(),
            "image auto contrast": self.checkBox_image_contrast.isChecked(),
            "image contour": self.checkBox_image_contour.isChecked(),
            "image zoom": self.checkBox_image_zoom.isChecked(),
            "trace raw": self.checkBox_trace_raw.isChecked(),
            "trace zoom": self.checkBox_trace_zoom.isChecked(),
        }
        state = {
            "plot": plot,
            "event": event,
        }
        return state

    def __setstate__(self, state):
        plot = state["plot"]
        for tb in self.signal_widgets:
            tb.blockSignals(True)
        # downsampling
        self.checkBox_downsample.setChecked(plot["downsampling"])
        self.spinBox_downsample.setValue(plot["downsampling value"])
        # axes combobox choices
        ds_features = self.rtdc_ds.features
        for cb in [self.comboBox_x, self.comboBox_y]:
            # set features
            cb.clear()
            for feat in dclab.dfn.scalar_feature_names:
                if feat in ds_features:
                    cb.addItem(dclab.dfn.feature_name2label[feat], feat)
        # axes labels
        idx = self.comboBox_x.findData(plot["axis x"])
        self.comboBox_x.setCurrentIndex(idx)
        idy = self.comboBox_y.findData(plot["axis y"])
        self.comboBox_y.setCurrentIndex(idy)
        # scaling
        idxs = self.comboBox_xscale.findData(plot["scale x"])
        self.comboBox_xscale.setCurrentIndex(idxs)
        idys = self.comboBox_yscale.findData(plot["scale y"])
        self.comboBox_yscale.setCurrentIndex(idys)
        # isoelastics
        self.checkBox_isoelastics.setChecked(plot["isoelastics"])
        for tb in self.signal_widgets:
            tb.blockSignals(False)
        if "event" in state:
            event = state["event"]
            self.checkBox_image_contrast.setChecked(
                event["image auto contrast"])
            self.checkBox_image_contour.setChecked(event["image contour"])
            self.checkBox_image_zoom.setChecked(event["image zoom"])
            self.spinBox_event.setValue(event["index"])
            self.checkBox_trace_raw.setChecked(event["trace raw"])

    def on_event_scatter_clicked(self, plot, point):
        """User clicked on scatter plot

        Parameters
        ----------
        plot: pg.PlotItem
            Active plot
        point: QPoint
            Selected point (determined by scatter plot widget)
        """
        # `self.on_tool` (`self.toolButton_event`) takes care of this:
        # self.widget_scatter.select.show()
        if not self.toolButton_event.isChecked():
            # emulate mouse toggle
            self.toolButton_event.setChecked(True)
            self.toolButton_event.toggled.emit(True)
        if self.widget_scatter.events_plotted is not None:
            # plotted events
            plotted = self.widget_scatter.events_plotted
            # get corrected index
            ds_idx = np.where(plotted)[0][point.index()]
            self.show_event(ds_idx)

    def on_event_scatter_spin(self, event):
        """Sping control for event selection changed"""
        self.show_event(event - 1)

    def on_event_scatter_update(self):
        """Just update the event shown"""
        event = self.spinBox_event.value()
        self.show_event(event - 1)

    def on_poly_create(self):
        """User wants to create a polygon filter"""
        self.pushButton_poly_create.setEnabled(False)
        if not self.toolButton_poly.isChecked():
            # emulate mouse toggle
            self.toolButton_poly.setChecked(True)
            self.toolButton_poly.toggled.emit(True)
        self.comboBox_poly.setEnabled(False)
        self.groupBox_poly.setEnabled(True)
        self.label_poly_create.setVisible(True)
        self.pushButton_poly_save.setVisible(True)
        self.pushButton_poly_cancel.setVisible(True)
        # defaults
        self.lineEdit_poly.setText("Polygon Filter {}".format(
            dclab.PolygonFilter._instance_counter + 1))
        self.checkBox_poly.setChecked(False)
        if self.widget_scatter.poly_line_roi is None:
            # add ROI only if there is nothing going on already
            plr = pg.PolyLineROI([], closed=True)
            plr.setPen("k")
            self.widget_scatter.poly_line_roi = plr
            self.widget_scatter.addItem(plr)
            self.widget_scatter.set_mouse_click_mode("poly-create")

    def on_poly_done(self):
        """User is done creating or modifying a polygon filter"""
        self.pushButton_poly_create.setEnabled(True)
        self.label_poly_create.setVisible(False)
        self.label_poly_modify.setVisible(False)
        self.pushButton_poly_save.setVisible(False)
        self.pushButton_poly_cancel.setVisible(False)
        if self.sender() == self.pushButton_poly_save:
            # save the polygon filter
            plr_state = self.widget_scatter.poly_line_roi.getState()
            points = [[p.x(), p.y()] for p in plr_state["points"]]
            name = self.lineEdit_poly.text()
            inverted = self.checkBox_poly.isChecked()
            axes = self.widget_scatter.xax, self.widget_scatter.yax
            # determine whether to create a new polygon filter or whether
            # to update an existing one.
            idp = self.comboBox_poly.currentData()
            if idp is None:
                dclab.PolygonFilter(axes=axes, points=points, name=name,
                                    inverted=inverted)
            else:
                pf = dclab.PolygonFilter.get_instance_from_id(idp)
                pf.name = name
                pf.inverted = inverted
                pf.points = points
        # remove the PolyLineRoi
        self.widget_scatter.removeItem(self.widget_scatter.poly_line_roi)
        self.widget_scatter.poly_line_roi = None
        self.widget_scatter.set_mouse_click_mode("scatter")
        self.update_polygon_panel()
        self.new_polygon_filter_created.emit()

    def on_poly_modify(self):
        """User wants to modify a polygon filter"""
        self.pushButton_poly_create.setEnabled(False)
        self.comboBox_poly.setEnabled(False)
        self.groupBox_poly.setEnabled(True)
        self.label_poly_modify.setVisible(True)
        self.pushButton_poly_save.setVisible(True)
        self.pushButton_poly_cancel.setVisible(True)
        # get the polygon filter id
        idp = self.comboBox_poly.currentData()
        pf = dclab.PolygonFilter.get_instance_from_id(idp)
        # set UI information
        self.lineEdit_poly.setText(pf.name)
        self.checkBox_poly.setChecked(pf.inverted)
        # set axes
        state = self.__getstate__()
        state["plot"]["axis x"] = pf.axes[0]
        state["plot"]["axis y"] = pf.axes[1]
        self.__setstate__(state)
        self.plot()
        # add ROI
        plr = pg.PolyLineROI(pf.points, closed=True)
        plr.setPen("k")
        self.widget_scatter.poly_line_roi = plr
        self.widget_scatter.addItem(plr)
        self.widget_scatter.set_mouse_click_mode("poly-modify")

    def on_tool(self):
        """Show and hide tools when the user selected a tool button"""
        toblock = [self.toolButton_event,
                   self.toolButton_poly,
                   self.toolButton_settings,
                   ]
        for b in toblock:
            b.blockSignals(True)
        # show extra data
        show_event = False
        show_poly = False
        show_settings = False
        sender = self.sender()
        if sender == self.toolButton_event:
            if self.toolButton_event.isChecked():
                show_event = True
        elif sender == self.toolButton_poly:
            if self.toolButton_poly.isChecked():
                show_poly = True
        elif sender == self.toolButton_settings:
            if self.toolButton_settings.isChecked():
                show_settings = True
        else:
            # keep everything as-is but update the sizes
            show_event = self.widget_event.isVisible()
            show_settings = self.widget_settings.isVisible()
            show_poly = self.widget_poly.isVisible()

        # toolbutton checked
        self.toolButton_event.setChecked(show_event)
        self.toolButton_poly.setChecked(show_poly)
        self.toolButton_settings.setChecked(show_settings)

        # widget visibility
        self.widget_event.setVisible(show_event)
        self.widget_scatter.select.setVisible(show_event)  # point in scatter
        self.widget_poly.setVisible(show_poly)
        self.widget_settings.setVisible(show_settings)

        if show_event:
            # update event plot (maybe axes changed)
            self.on_event_scatter_update()

        for b in toblock:
            b.blockSignals(False)

        # set size
        hide = show_event * show_settings * show_poly
        mdiwin = self.parent()
        geom = mdiwin.geometry()
        geom.setWidth(geom.width() - (-1)**hide * 300)
        mdiwin.setGeometry(geom)
        mdiwin.adjustSize()

    def plot(self):
        """Update the plot using the current state of the UI"""
        plot = self.__getstate__()["plot"]
        downsample = plot["downsampling"] * plot["downsampling value"]

        self.widget_scatter.plot_data(rtdc_ds=self.rtdc_ds,
                                      downsample=downsample,
                                      xax=plot["axis x"],
                                      yax=plot["axis y"],
                                      xscale=plot["scale x"],
                                      yscale=plot["scale y"],
                                      isoelastics=plot["isoelastics"])
        # make sure the correct plot items are visible (e.g. scatter select)
        self.on_tool()
        # update polygon filter axis names
        self.label_poly_x.setText(dclab.dfn.feature_name2label[plot["axis x"]])
        self.label_poly_y.setText(dclab.dfn.feature_name2label[plot["axis y"]])

    def show_event(self, event):
        """Display the event data (image, contour, trace)

        Parameters
        ----------
        event: int or None
            Event index of the dataset; indices start at 0
            If set to None, the index from `self.spinBox_event`
            will be used.
        """
        # Update spin box data
        self.spinBox_event.blockSignals(True)
        self.spinBox_event.setValue(event + 1)
        self.spinBox_event.blockSignals(False)

        # Update selection point in scatter plot
        self.widget_scatter.setSelection(event)
        imkw = self.imkw.copy()
        # update image
        state = self.__getstate__()
        ds = self.rtdc_ds
        if "image" in ds:
            cellimg = ds["image"][event]
            if state["event"]["image auto contrast"]:
                imkw["levels"] = cellimg.min(), cellimg.max()
            # convert to RGB
            cellimg = cellimg.reshape(
                cellimg.shape[0], cellimg.shape[1], 1)
            cellimg = np.repeat(cellimg, 3, axis=2)
            # Only load contour data if there is an image column.
            # We don't know how big the images should be so we
            # might run into trouble displaying random contours.
            if "mask" in ds and len(ds["mask"]) > event:
                mask = ds["mask"][event]
                if state["event"]["image contour"]:
                    # compute contour image from mask
                    cont = mask ^ binary_erosion(mask)
                    # set red contour pixel values in original image
                    cellimg[cont, 0] = int(imkw["levels"][1]*.7)
                    cellimg[cont, 1] = 0
                    cellimg[cont, 2] = 0
                if state["event"]["image zoom"]:
                    xv, yv = np.where(mask)
                    idminx = xv.min() - 5
                    idminy = yv.min() - 5
                    idmaxx = xv.max() + 5
                    idmaxy = yv.max() + 5
                    idminx = idminx if idminx >= 0 else 0
                    idminy = idminy if idminy >= 0 else 0
                    shx, shy = mask.shape
                    idmaxx = idmaxx if idmaxx < shx else shx
                    idmaxy = idmaxy if idmaxy < shy else shy
                    cellimg = cellimg[idminx:idmaxx, idminy:idmaxy]
            self.imageView_image.setImage(cellimg, **imkw)
            self.groupBox_image.show()
        else:
            self.groupBox_image.hide()

        if "trace" in ds:
            # time axis
            flsamples = ds.config["fluorescence"]["samples per event"]
            flrate = ds.config["fluorescence"]["sample rate"]
            fltime = np.arange(flsamples) / flrate * 1e6
            # temporal range (min, max, fl-peak-maximum)
            range_t = [fltime[0], fltime[-1], 0]
            # fluorescence intensity
            range_fl = [0, 0]
            for key in dclab.dfn.FLUOR_TRACES:
                if key.count("raw") and not state["event"]["trace raw"]:
                    # hide raw trace data if user decided so
                    show = False
                else:
                    show = True
                flid = key.split("_")[0]
                if (key in ds["trace"] and show):
                    # show the trace information
                    tracey = ds["trace"][key][event]  # trace data
                    range_fl[0] = min(range_fl[0], tracey.min())
                    range_fl[1] = max(range_fl[1], tracey.max())
                    self.trace_plots[key].setData(fltime, tracey)
                    self.trace_plots[key].show()
                    if state["event"]["trace zoom"]:
                        flpos = ds["{}_pos".format(flid)][event]
                        flwidth = ds["{}_width".format(flid)][event]
                        flmax = ds["{}_max".format(flid)][event]
                        # use the peak maximum to decide which range to use
                        if flmax > range_t[2]:
                            range_t[0] = flpos - 1.5 * flwidth
                            range_t[1] = flpos + 1.5 * flwidth
                            range_t[2] = flmax
                else:
                    self.trace_plots[key].hide()
            self.graphicsView_trace.setXRange(*range_t[:2], padding=0)
            if range_fl[0] != range_fl[1]:
                self.graphicsView_trace.setYRange(*range_fl, padding=.01)
            self.graphicsView_trace.setLimits(xMin=0, xMax=fltime[-1])
            self.groupBox_trace.show()
        else:
            self.groupBox_trace.hide()

        # update features tab
        # Disable updates which look ugly when the user switches quickly
        self.tableWidget_feats.setUpdatesEnabled(False)
        # only use computed features (speed)
        fcands = ds.features_loaded
        # restrict to scalar features
        feats = [f for f in fcands if f in dclab.dfn.scalar_feature_names]
        lf = sorted([(dclab.dfn.feature_name2label[f], f) for f in feats])
        self.tableWidget_feats.setRowCount(len(feats))
        self.tableWidget_feats.setColumnCount(2)
        self.tableWidget_feats.setVerticalHeaderLabels(feats)
        for ii, (lii, fii) in enumerate(lf):
            name_vis = lii if len(lii) < 20 else lii[:17] + "..."
            label_name = QtWidgets.QLabel(name_vis)
            label_name.setToolTip(lii)
            value = ds[fii][event]
            if np.isnan(value) or np.isinf(value):
                fmt = "{}"
            elif fii in idiom.INTEGER_FEATURES:
                fmt = "{:.0f}"
            elif value == 0:
                fmt = "{:.1f}"
            else:
                dec = -int(np.ceil(np.log(np.abs(value)))) + 3
                if dec <= 0:
                    dec = 1
                fmt = "{:." + "{}".format(dec) + "f}"
            label_value = QtWidgets.QLabel(fmt.format(value))
            label_value.setToolTip(lii)
            self.tableWidget_feats.setCellWidget(ii, 0, label_name)
            self.tableWidget_feats.setCellWidget(ii, 1, label_value)
        header = self.tableWidget_feats.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        # enable updates again
        self.tableWidget_feats.setUpdatesEnabled(True)

    @QtCore.pyqtSlot(dclab.rtdc_dataset.RTDCBase)
    def show_rtdc(self, rtdc_ds):
        """Display an RT-DC measurement given by `path` and `filters`"""
        # make things visible
        self.label_howto.hide()
        self.widget_scatter.show()
        self.widget_tool.setEnabled(True)
        # get the state
        state = self.__getstate__()
        plot = state["plot"]
        # remove event state (ill-defined for different datasets)
        state.pop("event")
        self.rtdc_ds = rtdc_ds
        # default features (plot axes)
        if plot["axis x"] is None:
            plot["axis x"] = "area_um"
        if plot["axis y"] is None:
            plot["axis y"] = "deform"
        # check whether axes exist in ds and change them if necessary
        ds_features = rtdc_ds.features
        if plot["axis x"] not in ds_features:
            for feat in dclab.dfn.scalar_feature_names:
                if feat in ds_features:
                    plot["axis x"] = feat
                    break
        if plot["axis y"] not in ds_features:
            for feat in dclab.dfn.scalar_feature_names:
                if feat in ds_features:
                    plot["axis y"] = feat
                    if feat != plot["axis y"]:
                        # If there is only one feature, at least we
                        # have set the state to a reasonable value.
                        break
        # set control ranges
        event_count = rtdc_ds.config["experiment"]["event count"]

        self.spinBox_event.blockSignals(True)
        self.spinBox_event.setMaximum(event_count)
        self.spinBox_event.setToolTip("total: {}".format(event_count))
        self.spinBox_event.setValue(1)
        self.spinBox_event.blockSignals(False)

        # set quick view state
        self.__setstate__(state)
        # scatter plot
        self.plot()
        # select first event in event viewer (also updates selection point)
        self.show_event(0)
        # this only updates the size of the tools (because there is no
        # sender)
        self.on_tool()

    def update_polygon_panel(self):
        """Update polygon filter combobox etc."""
        pfts = dclab.PolygonFilter.instances
        if pfts:
            self.comboBox_poly.blockSignals(True)
            self.comboBox_poly.clear()
            self.comboBox_poly.addItem("Choose...", None)
            for pf in pfts:
                self.comboBox_poly.addItem(pf.name, pf.unique_id)
            self.comboBox_poly.blockSignals(False)
            self.comboBox_poly.setEnabled(True)
        else:
            self.comboBox_poly.setEnabled(False)
        self.groupBox_poly.setEnabled(False)


class CustomViewBox(pg.ViewBox):
    set_scatter_point = QtCore.pyqtSignal(QtCore.QPointF)
    add_poly_vertex = QtCore.pyqtSignal(QtCore.QPointF)

    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.mode = "scatter"

    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton:
            pos = self.mapToView(ev.pos())
            if self.mode == "scatter":
                self.set_scatter_point.emit(pos)
            elif self.mode == "poly-create":
                self.add_poly_vertex.emit(pos)
            ev.accept()
        else:
            ev.ignore()


class RTDCScatterWidget(pg.PlotWidget):
    def __init__(self, *args, **kwargs):
        self._view_box = CustomViewBox()
        super(RTDCScatterWidget, self).__init__(viewBox=self._view_box,
                                                *args, **kwargs)
        self.scatter = RTDCScatterPlot()
        self.select = pg.PlotDataItem(x=[1], y=[2], symbol="o")
        #: List of isoelasticity line plots
        self.isoelastics = []
        self.addItem(self.scatter)
        self.addItem(self.select)
        self.select.hide()
        self.xscale = "linear"
        self.yscale = "linear"
        #: Boolean array identifying the plotted events w.r.t. the full
        #: dataset
        self.events_plotted = None
        #: Unfiltered and not-downsampled x component of current scatter plot
        self.data_x = None
        #: Unfiltered and not-downsampled y component of current scatter plot
        self.data_y = None

        # General plot options
        # show top and right axes, but not ticklabels
        for kax in ["top", "right"]:
            self.plotItem.showAxis(kax)
            ax = self.plotItem.axes[kax]["item"]
            ax.setTicks([])
        # show grid
        self.plotItem.showGrid(x=True, y=True, alpha=.1)
        self.poly_line_roi = None

        # Signals for mouse click
        # let view box update the selected event in the scatter plot
        self._view_box.set_scatter_point.connect(self.scatter.set_point)
        # let view box update self.poly_line_roi
        self._view_box.add_poly_vertex.connect(self.add_poly_vertex)

    def add_poly_vertex(self, pos):
        state = self.poly_line_roi.getState()
        state["points"].append([pos.x(), pos.y()])
        self.poly_line_roi.setState(state)

    def plot_data(self, rtdc_ds, xax="area_um", yax="deform", downsample=False,
                  xscale="linear", yscale="linear", isoelastics=False):
        self.rtdc_ds = rtdc_ds
        self.xax = xax
        self.yax = yax
        x, y, kde, idx = plot_cache.get_scatter_data(
            rtdc_ds=self.rtdc_ds,
            downsample=downsample,
            xax=self.xax,
            yax=self.yax,
            xscale=self.xscale,
            yscale=self.yscale)
        self.events_plotted = idx
        self.data_x = self.rtdc_ds[self.xax]
        self.data_y = self.rtdc_ds[self.yax]
        # define colormap
        # TODO: improve speed?
        brush = []
        kde -= kde.min()
        kde /= kde.max()
        num_hues = 500
        for k in kde:
            color = pg.intColor(int(k*num_hues), num_hues)
            brush.append(color)
        # convert to log-scale if applicable
        if xscale == "log":
            x = np.log10(x)
        if yscale == "log":
            y = np.log10(y)
        # set data
        self.scatter.setData(x=x, y=y, brush=brush)
        # set log mode
        self.plotItem.setLogMode(x=xscale == "log",
                                 y=yscale == "log")
        # reset range (in case user modified it manually)
        # (For some reason, we have to do this twice...)
        self.plotItem.setRange(xRange=(x.min(), x.max()),
                               yRange=(y.min(), y.max()),
                               padding=.05)
        self.plotItem.setRange(xRange=(x.min(), x.max()),
                               yRange=(y.min(), y.max()),
                               padding=.05)

        self.plotItem.setLabels(
            left=dclab.dfn.feature_name2label[self.yax],
            bottom=dclab.dfn.feature_name2label[self.xax])

        # Force updating the plot item size, otherwise axes labels
        # may have an offset.
        s = self.plotItem.size()
        self.plotItem.resize(s.width()+1, s.height())
        self.plotItem.resize(s)

        # Isoelastics
        # remove old isoelastics
        for lp in self.isoelastics:
            self.removeItem(lp)
        if isoelastics:
            cfg = self.rtdc_ds.config
            self.isoelastics = pipeline_plot.add_isoelastics(
                plot_widget=self,
                axis_x=self.xax,
                axis_y=self.yax,
                channel_width=cfg["setup"]["channel width"],
                pixel_size=cfg["imaging"]["pixel size"])

    def set_mouse_click_mode(self, mode):
        allowed = ["scatter", "poly-create", "poly-modify"]
        if mode not in allowed:
            raise ValueError("Invalid mouse mode: {}, ".format(mode)
                             + "expected one of {}".format(allowed))
        if mode in ["poly-create", "poly-modify"]:
            if self.poly_line_roi is None:
                raise ValueError("Please set self.poly_line_roi before "
                                 + "setting the click mode!")
        self._view_box.mode = mode

    def setSelection(self, event_index):
        x = self.data_x[event_index]
        y = self.data_y[event_index]
        # workaround, because ScatterPlotItem does somehow not support
        # logarithmic scaling. Surprisingly, this works very well when
        # the log-scaling is changed (data is rescaled).
        if self.xscale == "log":
            x = 10**x
        if self.yscale == "log":
            y = 10**y
        self.select.setData([x], [y])


class RTDCScatterPlot(pg.ScatterPlotItem):
    def __init__(self, size=3, pen=pg.mkPen(color=(0, 0, 0, 0)),
                 brush=pg.mkBrush("k"),
                 *args, **kwargs):
        super(RTDCScatterPlot, self).__init__(size=size,
                                              pen=pen,
                                              brush=brush,
                                              symbol="s",
                                              *args,
                                              **kwargs)
        self.setData(x=range(10), y=range(10))

    def pointAt(self, pos):
        """Unlike `ScatterPlotItem.pointsAt`, return the closest point"""
        x = pos.x()
        y = pos.y()
        pw = self.pixelWidth()
        ph = self.pixelHeight()
        p = self.points()[0]
        d = np.inf
        for s in self.points():
            sp = s.pos()
            di = ((sp.x() - x)/pw)**2 + ((sp.y() - y)/ph)**2
            if di < d:
                p = s
                d = di
        return p

    def set_point(self, view_pos):
        pos = self.mapFromView(view_pos)
        pt = self.pointAt(pos)
        self.ptClicked = pt
        self.sigClicked.emit(self, self.ptClicked)

    def mouseClickEvent(self, ev):
        """Override that return only a single point using `pointAt`"""
        ev.ignore()  # clicks are handles by CustomViewBox
        if False:
            if ev.button() == QtCore.Qt.LeftButton:
                pt = self.pointAt(ev.pos())
                self.ptClicked = pt
                self.sigClicked.emit(self, self.ptClicked)
                ev.accept()
            else:
                ev.ignore()
