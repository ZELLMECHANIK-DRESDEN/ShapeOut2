import pkg_resources

import dclab
from dclab import kde_contours
import numpy as np
from PyQt5 import uic, QtCore, QtWidgets
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
        dslist, slot_states = self.pipeline.get_plot_datasets(self.identifier)
        plot = Plot.get_instances()[self.identifier]
        plot_state = plot.__getstate__()
        # Plot size and title
        gen = plot_state["general"]
        parent = self.parent()
        self.setWindowTitle(gen["name"])
        self.setMinimumSize(gen["size x"], gen["size y"])
        self.setMaximumSize(gen["size x"], gen["size y"])
        size_hint = self.parent().sizeHint()
        parent.setMinimumSize(size_hint)
        parent.setMaximumSize(size_hint)
        self.plot.redraw(dslist, slot_states, plot_state)


class PipelinePlotWidget(pg.PlotWidget):
    def __init__(self, *args, **kwargs):
        super(PipelinePlotWidget, self).__init__(*args, **kwargs)
        # Disable user interaction
        self.plotItem.setMouseEnabled(x=False, y=False)
        self.plotItem.setMenuEnabled(False)
        self.plotItem.hideButtons()
        self._plot_elements = []
        # General plot options
        # show top and right axes, but not ticklabels
        for kax in ["top", "right"]:
            self.plotItem.showAxis(kax)
            ax = self.plotItem.axes[kax]["item"]
            ax.setTicks([])
        # show grid
        self.plotItem.showGrid(x=True, y=True, alpha=.1)

    def redraw(self, dslist, slot_states, plot_state):
        # Remove everything
        for el in self._plot_elements:
            self.removeItem(el)

        if not dslist:
            return
        # General
        gen = plot_state["general"]
        set_axes_labels(self.plotItem, plot_state, slot_states)
        # TODO:
        # - test whether all datasets have same channel width / pixel size
        # Isoelastics
        if gen["isoelastics"]:
            cfg = dslist[0].config
            els = add_isoelastics(plot_widget=self,
                                  axis_x=gen["axis x"],
                                  axis_y=gen["axis y"],
                                  channel_width=cfg["setup"]["channel width"],
                                  pixel_size=cfg["imaging"]["pixel size"])
            self._plot_elements += els
        # Set Range
        self.plotItem.setRange(xRange=gen["range x"],
                               yRange=gen["range y"],
                               padding=0,
                               )
        # Set Log scale
        self.plotItem.setLogMode(x=gen["scale x"] == "log",
                                 y=gen["scale y"] == "log")
        # Scatter data
        if plot_state["scatter"]["enabled"]:
            for rtdc_ds, ss in zip(dslist, slot_states):
                sct = add_scatter(plot_widget=self,
                                  rtdc_ds=rtdc_ds,
                                  plot_state=plot_state,
                                  slot_state=ss
                                  )
                self._plot_elements += sct
        # Contour data
        if plot_state["contour"]["enabled"]:
            for rtdc_ds, ss in zip(dslist, slot_states):
                con = add_contour(plot_widget=self,
                                  rtdc_ds=rtdc_ds,
                                  plot_state=plot_state,
                                  slot_state=ss
                                  )
                self._plot_elements += con


def add_contour(plot_widget, plot_state, rtdc_ds, slot_state):
    gen = plot_state["general"]
    con = plot_state["contour"]
    x, y, density = plot_cache.get_contour_data(
        rtdc_ds=rtdc_ds,
        xax=gen["axis x"],
        yax=gen["axis y"],
        xacc=con["spacing x"],
        yacc=con["spacing y"],
        xscale=gen["scale x"],
        yscale=gen["scale y"],
        kde_type=gen["kde"],
    )
    plev = kde_contours.get_quantile_levels(
        density=density,
        x=x,
        y=y,
        xp=rtdc_ds[gen["axis x"]][rtdc_ds.filter.all],
        yp=rtdc_ds[gen["axis y"]][rtdc_ds.filter.all],
        q=np.array(con["percentiles"])/100,
        normalize=True)
    contours = []
    for level in plev:
        cc = kde_contours.find_contours_level(density, x=x, y=y, level=level)
        contours.append(cc)

    elements = []
    for ii in range(len(contours)):
        style = linestyles[con["line styles"][ii]]
        width = con["line widths"][ii]
        for cci in contours[ii]:
            cline = pg.PlotDataItem(x=cci[:, 0],
                                    y=cci[:, 1],
                                    pen=pg.mkPen(color=slot_state["color"],
                                                 width=width,
                                                 style=style,
                                                 ),
                                    )
            elements.append(cline)
            plot_widget.addItem(cline)
    return elements


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


def add_scatter(plot_widget, plot_state, rtdc_ds, slot_state):
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
            brush.append(pg.intColor(int(k*num_hues), num_hues))
    elif sca["marker hue"] == "feature":
        brush = []
        feat = rtdc_ds[sca["hue feature"]][idx]
        feat -= feat.min()
        feat /= feat.max()
        num_hues = 500
        for f in feat:
            brush.append(pg.intColor(int(f*num_hues), num_hues))
    elif sca["marker hue"] == "dataset":

        brush = pg.mkBrush(slot_state["color"])
    else:
        brush = pg.mkBrush("k")
    # convert to log-scale if applicable
    if gen["scale x"] == "log":
        x = np.log10(x)
    if gen["scale y"] == "log":
        y = np.log10(y)

    scatter.setData(x=x, y=y, brush=brush)
    return [scatter]


def set_axes_labels(plot_item, plot_state, slot_states):
    gen = plot_state["general"]
    labelx = dclab.dfn.feature_name2label[gen["axis x"]]
    labely = dclab.dfn.feature_name2label[gen["axis y"]]
    # replace FL-? with user-defined names
    fl_names = slot_states[0]["fl names"]
    if labelx.count("FL"):
        for key in fl_names:
            if key in labelx:
                labelx = labelx.replace(key, fl_names[key])
                break
    if labely.count("FL"):
        for key in fl_names:
            if key in labelx:
                labelx = labelx.replace(key, fl_names[key])
                break
    plot_item.setLabels(left=labely, bottom=labelx)


linestyles = {
    "solid": QtCore.Qt.SolidLine,
    "dashed": QtCore.Qt.DashLine,
    "dotted": QtCore.Qt.DotLine,
}
