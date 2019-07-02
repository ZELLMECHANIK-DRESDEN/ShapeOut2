import pathlib
import pkg_resources

import dclab
from PyQt5 import uic, QtCore, QtWidgets
import pyqtgraph as pg


class QuickView(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "quick_view.ui")
        uic.loadUi(path_ui, self)
        self.setWindowTitle("Quick View")
        self.scatter_plot = self.widget_scatter.plot
        self.scatter_plot.sigClicked.connect(self.clicked)

    def clicked(self, plot, points):
        for p in plot.lastClicked:
            p.resetPen()
        print("clicked points", points)
        for p in points:
            p.setPen('b', width=2)
        plot.lastClicked = points

    @QtCore.pyqtSlot(pathlib.Path, list)
    def show_rtdc(self, path, filters):
        axis_x = "area_um"
        axis_y = "deform"
        ds = dclab.new_dataset(path)
        self.scatter_plot.clear()
        self.scatter_plot.setData(x=ds[axis_x], y=ds[axis_y])


class RTDCScatterWidget(pg.PlotWidget):
    def __init__(self, *args, **kwargs):
        super(RTDCScatterWidget, self).__init__(*args, **kwargs)
        self.plot = RTDCScatterPlot()
        self.addItem(self.plot)


class RTDCScatterPlot(pg.ScatterPlotItem):
    def __init__(self, size=10, pen=pg.mkPen("k"),
                 brush=pg.mkBrush(255, 255, 255, 120),
                 *args, **kwargs):
        super(RTDCScatterPlot, self).__init__(size=size,
                                              pen=pen,
                                              brush=brush,
                                              *args, **kwargs)
        self.lastClicked = []
        self.setData(x=range(10), y=range(10))
