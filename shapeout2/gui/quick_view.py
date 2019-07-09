import pathlib
import pkg_resources

import dclab
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
        self.scatter_plot = self.widget_scatter.plot
        self.scatter_plot.sigClicked.connect(self.clicked)

        # Set scale options (with data)
        for cb in [self.comboBox_xscale, self.comboBox_yscale]:
            cb.clear()
            cb.addItem("linear", "linear")
            cb.addItem("logarithmic", "log")

        # Hide settings by default
        self.tabWidget.setVisible(False)

        # initial value
        self.path = None
        self.filters = []

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

    def clicked(self, plot, points):
        for p in plot.lastClicked:
            p.resetPen()
        print("clicked points", points)
        for p in points:
            p.setPen('b', width=2)
        plot.lastClicked = points

    def plot(self):
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

        self.scatter_plot.clear()
        self.widget_scatter.plotItem.setLogMode(x=state["scale x"] == "log",
                                                y=state["scale y"] == "log")
        self.scatter_plot.setData(x=x, y=y, brush=brush)
        self.widget_scatter.plotItem.setLabels(
            left=dclab.dfn.feature_name2label[state["axis y"]],
            bottom=dclab.dfn.feature_name2label[state["axis x"]])
        # TODO: draw isoelasticity lines

    @QtCore.pyqtSlot(pathlib.Path, list)
    def show_rtdc(self, path, filters):
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
        self.plot()


class RTDCScatterWidget(pg.PlotWidget):
    def __init__(self, *args, **kwargs):
        super(RTDCScatterWidget, self).__init__(*args, **kwargs)
        self.plot = RTDCScatterPlot()
        self.addItem(self.plot)


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
        self.lastClicked = []
        self.setData(x=range(10), y=range(10))
