import pkg_resources

import dclab
import numpy as np
from PyQt5 import uic, QtCore, QtWidgets
import pyqtgraph as pg
from scipy.ndimage import binary_erosion

from .. import plot_cache


class QuickView(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "quick_view.ui")
        uic.loadUi(path_ui, self)
        self.setWindowTitle("Quick View (QV)")

        # Scatter plot
        self.scatter_plot = self.widget_scatter.scatter

        # Set scale options (with data)
        for cb in [self.comboBox_xscale, self.comboBox_yscale]:
            cb.clear()
            cb.addItem("linear", "linear")
            cb.addItem("logarithmic", "log")

        # Hide settings/events by default
        self.widget_event.setVisible(False)
        self.widget_settings.setVisible(False)

        #: Boolean array identifying the plotted events w.r.t. the full
        #: dataset
        self.events_plotted = None
        #: Unfiltered and not-downsampled x component of current scatter plot
        self.data_x = None
        #: Unfiltered and not-downsampled y component of current scatter plot
        self.data_y = None

        # settings button
        self.toolButton_settings.toggled.connect(self.on_tool)
        self.toolButton_event.toggled.connect(self.on_tool)

        # event changed signal
        self.scatter_plot.sigClicked.connect(self.on_event_scatter_clicked)
        self.spinBox_event.valueChanged.connect(self.on_event_scatter_spin)
        self.checkBox_contour.stateChanged.connect(
            self.on_event_scatter_update)
        self.checkBox_zoom_roi.stateChanged.connect(
            self.on_event_scatter_update)
        self.checkBox_auto_contrast.stateChanged.connect(
            self.on_event_scatter_update)
        self.checkBox_raw_trace.stateChanged.connect(
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

        #: default parameters for the event image
        self.imkw = dict(autoLevels=False,
                         levels=(0, 254),
                         )

    def __getstate__(self):
        plot = {
            "downsampling enabled": self.checkBox_downsample.isChecked(),
            "downsampling value": self.spinBox_downsample.value(),
            "axis x": self.comboBox_x.currentData(),
            "axis y": self.comboBox_y.currentData(),
            "scale x": self.comboBox_xscale.currentData(),
            "scale y": self.comboBox_yscale.currentData(),
            "isoelastics enabled": self.checkBox_isoelastics.isChecked(),
        }
        event = {
            "index": self.spinBox_event.value(),
            "image auto contrast": self.checkBox_auto_contrast.isChecked(),
            "image contour": self.checkBox_contour.isChecked(),
            "image zoom": self.checkBox_zoom_roi.isChecked(),
            "trace raw": self.checkBox_raw_trace.isChecked(),
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
        self.checkBox_downsample.setChecked(plot["downsampling enabled"])
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
        self.checkBox_isoelastics.setChecked(plot["isoelastics enabled"])
        for tb in self.signal_widgets:
            tb.blockSignals(False)
        if "event" in state:
            self.checkBox_auto_contrast.setChecked(
                state["image auto contrast"])
            self.checkBox_contour.setChecked(state["image contour"])
            self.checkBox_zoom_roi.setChecked(state["event"]["image zoom"])
            self.spinBox_event.setValue(state["event"]["index"])
            self.checkBox_raw_trace.setChecked(state["event"]["trace raw"])

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
        if self.events_plotted is not None:
            # get corrected index
            ds_idx = np.where(self.events_plotted)[0][point.index()]
            self.show_event(ds_idx)

    def on_event_scatter_spin(self, event):
        """Sping control for event selection changed"""
        self.show_event(event - 1)

    def on_event_scatter_update(self):
        """Just update the event shown"""
        event = self.spinBox_event.value()
        self.show_event(event - 1)

    def on_tool(self):
        """Show and hide tools when the user selected a tool button"""
        # show extra data
        show_event = False
        show_settings = False
        sender = self.sender()
        if sender == self.toolButton_settings:
            if self.toolButton_settings.isChecked():
                show_settings = True
                self.toolButton_event.setChecked(False)
        elif sender == self.toolButton_event:
            if self.toolButton_event.isChecked():
                show_event = True
                self.toolButton_settings.setChecked(False)
        else:
            # keep everything as-is but update the sizes
            show_event = self.widget_event.isVisible()
            show_settings = self.widget_settings.isVisible()
        self.widget_event.setVisible(show_event)
        self.widget_scatter.select.setVisible(show_event)

        self.widget_settings.setVisible(show_settings)
        # set size
        show = show_event * show_settings
        mdiwin = self.parent()
        geom = mdiwin.geometry()
        geom.setWidth(geom.width() - (-1)**show * 300)
        mdiwin.setGeometry(geom)
        mdiwin.adjustSize()

    def plot(self):
        """Update the plot using the current state of the UI"""
        plot = self.__getstate__()["plot"]
        downsample = plot["downsampling enabled"] * \
            plot["downsampling value"]
        x, y, kde, idx = plot_cache.get_scatter_data(
            rtdc_ds=self.rtdc_ds,
            downsample=downsample,
            xax=plot["axis x"],
            yax=plot["axis y"],
            xscale=plot["scale x"],
            yscale=plot["scale y"])
        self.events_plotted = idx
        self.data_x = self.rtdc_ds[plot["axis x"]]
        self.data_y = self.rtdc_ds[plot["axis y"]]
        # define colormap
        # TODO: improve speed?
        brush = []
        kde -= kde.min()
        kde /= kde.max()
        num_hues = 500
        for k in kde:
            color = pg.intColor(int(k*num_hues), num_hues)
            brush.append(color)

        self.widget_scatter.setData(x=x,
                                    y=y,
                                    brush=brush,
                                    xscale=plot["scale x"],
                                    yscale=plot["scale y"])

        self.widget_scatter.plotItem.setLabels(
            left=dclab.dfn.feature_name2label[plot["axis y"]],
            bottom=dclab.dfn.feature_name2label[plot["axis x"]])
        # Force updating the plot item size, otherwise axes labels
        # may have an offset.
        s = self.widget_scatter.plotItem.size()
        self.widget_scatter.plotItem.resize(s.width()+1, s.height())
        self.widget_scatter.plotItem.resize(s)
        # TODO: draw isoelasticity lines

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
        self.widget_scatter.setSelection(self.data_x[event],
                                         self.data_y[event])
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
            for key in dclab.dfn.FLUOR_TRACES:
                if key.count("raw") and not state["event"]["trace raw"]:
                    # hide raw trace data if user decided so
                    show = False
                else:
                    show = True
                if (key in ds["trace"] and show):
                    # show the trace information
                    tracey = ds["trace"][key][event]  # trace data
                    tracex = np.arange(tracey.size)  # time data
                    self.trace_plots[key].setData(tracex, tracey)
                    self.trace_plots[key].show()
                else:
                    self.trace_plots[key].hide()
            self.graphicsView_trace.setXRange(0, tracey.size, padding=0)
            self.graphicsView_trace.setLimits(xMin=0, xMax=tracey.size)
            self.groupBox_trace.show()
        else:
            self.groupBox_trace.hide()

    @QtCore.pyqtSlot(dclab.rtdc_dataset.RTDCBase)
    def show_rtdc(self, rtdc_ds):
        """Display an RT-DC measurement given by `path` and `filters`"""
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


class RTDCScatterWidget(pg.PlotWidget):
    def __init__(self, *args, **kwargs):
        super(RTDCScatterWidget, self).__init__(*args, **kwargs)
        self.scatter = RTDCScatterPlot()
        self.select = pg.PlotDataItem(x=[1], y=[2], symbol="o")
        self.addItem(self.scatter)
        self.addItem(self.select)
        self.select.hide()
        self.logx = False
        self.logy = False

    def setData(self, x, y, brush, xscale="linear", yscale="linear"):
        if xscale == "log":
            x = np.log10(x)
            logx = True
        else:
            logx = False

        if yscale == "log":
            y = np.log10(y)
            logy = True
        else:
            logy = False

        # set data
        self.scatter.setData(x=x, y=y, brush=brush)
        # set log mode
        self.plotItem.setLogMode(x=logx, y=logy)
        self.logx = logx
        self.logy = logy
        # reset range (in case user modified it manually)
        # (For some reason, we have to do this twice...)
        self.plotItem.setRange(xRange=(x.min(), x.max()),
                               yRange=(y.min(), y.max()),
                               padding=.05)
        self.plotItem.setRange(xRange=(x.min(), x.max()),
                               yRange=(y.min(), y.max()),
                               padding=.05)

    def setSelection(self, x, y):
        # workaround, because ScatterPlotItem does somehow not support
        # logarithmic scaling. Surprisingly, this works very well when
        # the log-scaling is changed (data is rescaled).
        if self.logx:
            x = 10**x
        if self.logy:
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

    def mouseClickEvent(self, ev):
        """Override that return only a single point using `pointAt`"""
        if ev.button() == QtCore.Qt.LeftButton:
            pt = self.pointAt(ev.pos())
            self.ptClicked = pt
            self.sigClicked.emit(self, self.ptClicked)
            ev.accept()
        else:
            ev.ignore()
