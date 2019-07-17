import pathlib
import pkg_resources

import dclab
import numpy as np
from PyQt5 import uic, QtCore, QtWidgets
import pyqtgraph as pg

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
        self.scatter_plot.sigClicked.connect(self.clicked)

        # Set scale options (with data)
        for cb in [self.comboBox_xscale, self.comboBox_yscale]:
            cb.clear()
            cb.addItem("linear", "linear")
            cb.addItem("logarithmic", "log")

        # Hide settings/events by default
        self.widget_event.setVisible(False)
        self.widget_settings.setVisible(False)

        # initial value
        self.path = None
        self.filters = []

        # settings button
        self.toolButton_settings.toggled.connect(self.on_tool)
        self.toolButton_event.toggled.connect(self.on_tool)

        # value changed signals
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

    def __getstate__(self):
        state = {"path": self.path,
                 "downsampling enabled": self.checkBox_downsample.isChecked(),
                 "downsampling value": self.spinBox_downsample.value(),
                 "axis x": self.comboBox_x.currentData(),
                 "axis y": self.comboBox_y.currentData(),
                 "scale x": self.comboBox_xscale.currentData(),
                 "scale y": self.comboBox_yscale.currentData(),
                 "isoelastics enabled": self.checkBox_isoelastics.isChecked(),
                 "filters": self.filters,
                 }
        return state

    def __setstate__(self, state):
        for tb in self.signal_widgets:
            tb.blockSignals(True)
        self.path = state["path"]
        # downsampling
        self.checkBox_downsample.setChecked(state["downsampling enabled"])
        self.spinBox_downsample.setValue(state["downsampling value"])
        # axes combobox choices
        ds_features = meta_tool.get_rtdc_features(state["path"])
        for cb in [self.comboBox_x, self.comboBox_y]:
            # set features
            cb.clear()
            for feat in dclab.dfn.scalar_feature_names:
                if feat in ds_features:
                    cb.addItem(dclab.dfn.feature_name2label[feat], feat)
        # axes labels
        idx = self.comboBox_x.findData(state["axis x"])
        self.comboBox_x.setCurrentIndex(idx)
        idy = self.comboBox_y.findData(state["axis y"])
        self.comboBox_y.setCurrentIndex(idy)
        # scaling
        idxs = self.comboBox_xscale.findData(state["scale x"])
        self.comboBox_xscale.setCurrentIndex(idxs)
        idys = self.comboBox_yscale.findData(state["scale y"])
        self.comboBox_yscale.setCurrentIndex(idys)
        # isoelastics
        self.checkBox_isoelastics.setChecked(state["isoelastics enabled"])
        self.filters = state["filters"]
        for tb in self.signal_widgets:
            tb.blockSignals(False)

    def clicked(self, plot, point):
        pos = point.pos()
        self.widget_scatter.setSelection(pos.x(), pos.y())
        # `self.on_tool` takes care of this:
        # self.widget_scatter.select.show()
        if not self.toolButton_event.isChecked():
            # emulate mouse toggle
            self.toolButton_event.setChecked(True)
            self.toolButton_event.toggled.emit(True)

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
        state = self.__getstate__()
        downsample = state["downsampling enabled"] * \
            state["downsampling value"]
        x, y, kde = plot_cache.get_scatter_data(
            path=state["path"],
            filters=state["filters"],
            downsample=downsample,
            xax=state["axis x"],
            yax=state["axis y"],
            xscale=state["scale x"],
            yscale=state["scale y"])
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
                                    xscale=state["scale x"],
                                    yscale=state["scale y"])

        self.widget_scatter.plotItem.setLabels(
            left=dclab.dfn.feature_name2label[state["axis y"]],
            bottom=dclab.dfn.feature_name2label[state["axis x"]])
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
        state["path"] = path
        state["filters"] = filters
        # default features (plot axes)
        if state["axis x"] is None:
            state["axis x"] = "area_um"
        if state["axis y"] is None:
            state["axis y"] = "deform"
        # check whether axes exist in ds and change them if necessary
        ds_features = meta_tool.get_rtdc_features(path)
        if state["axis x"] not in ds_features:
            for feat in dclab.dfn.scalar_feature_names:
                if feat in ds_features:
                    state["axis x"] = feat
                    break
        if state["axis y"] not in ds_features:
            for feat in dclab.dfn.scalar_feature_names:
                if feat in ds_features:
                    state["axis y"] = feat
                    if feat != state["axis y"]:
                        # If there is only one feature, at least we
                        # have set the state to a reasonable value.
                        break
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
