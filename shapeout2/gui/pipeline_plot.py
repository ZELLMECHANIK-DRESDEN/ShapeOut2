import pkg_resources

import dclab
import numpy as np
from PyQt5 import uic, QtWidgets
import pyqtgraph as pg

from ..pipeline import Plot
from .. import plot_cache


class PipelinePlot(QtWidgets.QWidget):
    def __init__(self, parent, pipeline, plot_id, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent=parent, *args, **kwargs)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "pipeline_plot.ui")
        uic.loadUi(path_ui, self)
        self.pipeline = pipeline
        self.identifier = plot_id
        self.update_content()

    def update_content(self):
        datasets = self.pipeline.get_plot_datasets(self.identifier)
        plot = Plot.get_instances()[self.identifier]
        state = plot.__getstate__()
        # Plot size and title
        gen = state["general"]
        parent = self.parent()
        self.setWindowTitle(gen["name"])
        self.setMinimumSize(gen["size x"], gen["size y"])
        self.setMaximumSize(gen["size x"], gen["size y"])
        size_hint = self.parent().sizeHint()
        parent.setMinimumSize(size_hint)
        parent.setMaximumSize(size_hint)
        self.plot.redraw(datasets, state)


class PipelinePlotWidget(pg.PlotWidget):
    def __init__(self, *args, **kwargs):
        super(PipelinePlotWidget, self).__init__(*args, **kwargs)
        self._plot_elements = []

    def redraw(self, datasets, state):
        # Remove everything
        for el in self._plot_elements:
            self.removeItem(el)

        if not datasets:
            return
        # General
        gen = state["general"]
        self.plotItem.setLabels(
            left=dclab.dfn.feature_name2label[gen["axis y"]],
            bottom=dclab.dfn.feature_name2label[gen["axis x"]])
        # TODO:
        # - test whether all datasets have same channel width / pixel size
        # Isoelastics
        if gen["isoelastics"]:
            cfg = datasets[0].config
            els = add_isoelastics(plot_widget=self,
                                  axis_x=gen["axis x"],
                                  axis_y=gen["axis y"],
                                  channel_width=cfg["setup"]["channel width"],
                                  pixel_size=cfg["imaging"]["pixel size"])
            self._plot_elements += els
        # Set Log scale
        self.plotItem.setLogMode(x=gen["scale x"] == "log",
                                 y=gen["scale y"] == "log")
        # Scatter data
        if state["scatter"]["enabled"]:
            for rtdc_ds in datasets:
                sct = add_scatter(plot_widget=self,
                                  rtdc_ds=rtdc_ds,
                                  plot_state=state,
                                  )
                self._plot_elements += sct


def add_isoelastics(plot_widget, axis_x, axis_y, channel_width, pixel_size):
    elements = []
    isodef = dclab.isoelastics.get_default()
    # We do not use isodef.get_with_rtdcbase, because then the
    # isoelastics would be shifted according to flow rate and.
    # viscosity. We could do it, but for visualization there is
    # really no need and also, the plots then look the same as
    # in Shape-Out 1.
    try:
        iso = isodef.get(
            method="numerical",
            channel_width=channel_width,
            flow_rate=None,
            viscosity=None,
            col1=axis_x,
            col2=axis_y,
            add_px_err=True,
            px_um=pixel_size)
    except KeyError:
        pass
    else:
        for ss in iso:
            iline = pg.PlotDataItem(x=ss[:, 0], y=ss[:, 1])
            plot_widget.addItem(iline)
            elements.append(iline)
            # send them to the back
            iline.setZValue(-1)
    return elements


def add_scatter(plot_widget, plot_state, rtdc_ds):
    gen = plot_state["general"]
    sca = plot_state["scatter"]
    scatter = pg.ScatterPlotItem(size=sca["marker size"],
                                 pen=pg.mkPen(color=(0, 0, 0, 0)),
                                 brush=pg.mkBrush("k"),
                                 symbol="s")
    plot_widget.addItem(scatter)

    if sca["marker hue"] == "kde":
        kde_type = gen["kde"]
    else:
        kde_type = "none"

    x, y, kde, idx = plot_cache.get_scatter_data(
        rtdc_ds=rtdc_ds,
        downsample=sca["downsample"] * sca["downsampling value"],
        xax=gen["axis x"],
        yax=gen["axis y"],
        xscale=gen["scale x"],
        yscale=gen["scale y"],
        kde_type=kde_type,
    )
    # define colormap
    # TODO:
    # - improve speed?
    # - common code base with QuickView
    if sca["marker hue"] == "kde":
        brush = []
        kde -= kde.min()
        kde /= kde.max()
        num_hues = 500
        for k in kde:
            color = pg.intColor(int(k*num_hues), num_hues)
            brush.append(color)
    elif sca["marker hue"] == "feature":
        brush = []
        feat = rtdc_ds[sca["hue feature"]][idx]
        feat -= feat.min()
        feat /= feat.max()
        num_hues = 500
        for f in feat:
            color = pg.intColor(int(f*num_hues), num_hues)
            brush.append(color)
    elif sca["marker hue"] == "dataset":
        raise NotImplementedError("TODO")
    else:
        brush = pg.mkBrush("k")
    # convert to log-scale if applicable
    if gen["scale x"] == "log":
        x = np.log10(x)
    if gen["scale y"] == "log":
        y = np.log10(y)

    scatter.setData(x=x, y=y, brush=brush)
    return [scatter]
