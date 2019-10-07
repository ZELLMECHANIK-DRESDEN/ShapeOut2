import pathlib
import pkg_resources

import dclab
import numpy as np
from PyQt5 import uic, QtCore, QtWidgets
import pyqtgraph as pg
from scipy.ndimage import binary_erosion

from .. import meta_tool
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

        #: Path to the dataset
        self.path = None
        #: List of filters applied to the dataset
        self.filters = []
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
        for vim in [self.imageView_image, self.imageView_trace]:
            vim.ui.histogram.hide()
            vim.ui.roiBtn.hide()
            vim.ui.menuBtn.hide()
            # disable keyboard shortcuts
            vim.keyPressEvent = lambda _: None
            vim.keyReleaseEvent = lambda _: None

        #: default parameters for the event image
        self.imkw = dict(autoLevels=False,
                         levels=(0, 254),
                         )

    def __getstate__(self):
        plot = {"path": self.path,
                "downsampling enabled": self.checkBox_downsample.isChecked(),
                "downsampling value": self.spinBox_downsample.value(),
                "axis x": self.comboBox_x.currentData(),
                "axis y": self.comboBox_y.currentData(),
                "scale x": self.comboBox_xscale.currentData(),
                "scale y": self.comboBox_yscale.currentData(),
                "isoelastics enabled": self.checkBox_isoelastics.isChecked(),
                "filters": self.filters,
                }
        event = {"auto contrast": self.checkBox_auto_contrast.isChecked(),
                 "contour": self.checkBox_contour.isChecked(),
                 "index": self.spinBox_event.value(),
                 "zoom": self.checkBox_zoom_roi.isChecked(),
                 }
        state = {"plot": plot,
                 "event": event,
                 }
        return state

    def __setstate__(self, state):
        plot = state["plot"]
        for tb in self.signal_widgets:
            tb.blockSignals(True)
        self.path = plot["path"]
        # downsampling
        self.checkBox_downsample.setChecked(plot["downsampling enabled"])
        self.spinBox_downsample.setValue(plot["downsampling value"])
        # axes combobox choices
        ds_features = meta_tool.get_rtdc_features(plot["path"])
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
        self.filters = plot["filters"]
        for tb in self.signal_widgets:
            tb.blockSignals(False)
        if "event" in state:
            self.checkBox_auto_contrast.setChecked(state["auto contrast"])
            self.checkBox_contour.setChecked(state["contour"])
            self.spinBox_event.setValue(state["event"]["index"])
            self.checkBox_zoom_roi.setChecked(state["event"]["zoom"])

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
        with dclab.new_dataset(state["plot"]["path"]) as ds:
            if "image" in ds:
                cellimg = ds["image"][event]
                if state["event"]["auto contrast"]:
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
                    if state["event"]["contour"]:
                        # compute contour image from mask
                        cont = mask ^ binary_erosion(mask)
                        # set red contour pixel values in original image
                        cellimg[cont, 0] = int(imkw["levels"][1]*.7)
                        cellimg[cont, 1] = 0
                        cellimg[cont, 2] = 0
                    if state["event"]["zoom"]:
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
            else:
                cellimg = np.zeros((50, 50, 3))

            self.imageView_image.setImage(cellimg, **imkw)

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
            path=plot["path"],
            filters=plot["filters"],
            downsample=downsample,
            xax=plot["axis x"],
            yax=plot["axis y"],
            xscale=plot["scale x"],
            yscale=plot["scale y"])
        self.events_plotted = idx
        with dclab.new_dataset(plot["path"]) as ds:
            self.data_x = ds[plot["axis x"]]
            self.data_y = ds[plot["axis y"]]
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

    @QtCore.pyqtSlot(pathlib.Path, list)
    def show_rtdc(self, path, filters):
        """Display an RT-DC measurement given by `path` and `filters`"""
        state = self.__getstate__()
        plot = state["plot"]
        # remove event state (ill-defined for different datasets)
        state.pop("event")
        plot["path"] = path
        plot["filters"] = filters
        # default features (plot axes)
        if plot["axis x"] is None:
            plot["axis x"] = "area_um"
        if plot["axis y"] is None:
            plot["axis y"] = "deform"
        # check whether axes exist in ds and change them if necessary
        ds_features = meta_tool.get_rtdc_features(path)
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
        cfg = meta_tool.get_rtdc_config(path)
        event_count = cfg["experiment"]["event count"]

        self.spinBox_event.blockSignals(True)
        self.spinBox_event.setMaximum(event_count)
        self.spinBox_event.setValue(1)
        self.spinBox_event.blockSignals(False)

        # set quick view state
        self.__setstate__(state)
        self.widget_scatter.select.hide()
        self.plot()


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

        self.scatter.setData(x=x, y=y, brush=brush)
        self.plotItem.setLogMode(x=logx, y=logy)
        self.logx = logx
        self.logy = logy

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
