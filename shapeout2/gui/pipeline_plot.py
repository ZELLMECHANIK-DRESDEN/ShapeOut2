import copy
import pkg_resources

import dclab
from dclab import kde_contours
import numpy as np
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import pyqtgraph as pg

from ..pipeline import Plot
from .. import plot_cache
from .simple_plot_widget import SimplePlotItem


class PipelinePlot(QtWidgets.QWidget):
    """Implements the plotting pipeline using pyqtgraph"""
    instances = {}

    def __init__(self, parent, pipeline, plot_id, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent=parent, *args, **kwargs)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "pipeline_plot.ui")
        uic.loadUi(path_ui, self)
        self.pipeline = pipeline
        self.identifier = plot_id
        self.update_content()
        PipelinePlot.instances[plot_id] = self

    def update_content(self):
        dslist, slot_states = self.pipeline.get_plot_datasets(self.identifier)
        plot = Plot.get_instances()[self.identifier]
        plot_state = plot.__getstate__()
        # Plot size and title
        lay = plot_state["layout"]
        parent = self.parent()
        self.setWindowTitle(lay["name"])
        self.setMinimumSize(lay["size x"], lay["size y"])
        self.setMaximumSize(lay["size x"], lay["size y"])
        size_hint = self.parent().sizeHint()
        parent.setMinimumSize(size_hint)
        parent.setMaximumSize(size_hint)
        # clear widget
        self.plot_layout.clear()

        if not slot_states:
            return

        labelx, labely = get_axes_labels(plot_state, slot_states)

        # font size for plot title (default size + 2)
        size = "{}pt".format(QtGui.QFont().pointSize() + 2)
        self.plot_layout.addLabel(lay["name"], colspan=2, size=size)
        self.plot_layout.nextRow()

        self.plot_layout.addLabel(labely, angle=-90)
        linner = self.plot_layout.addLayout()
        self.plot_layout.nextRow()
        self.plot_layout.addLabel(labelx, col=1)

        if lay["division"] == "merge":
            pp = PipelinePlotItem(parent=linner)
            linner.addItem(item=pp,
                           row=None,
                           col=None,
                           rowspan=1,
                           colspan=1)
            pp.redraw(dslist, slot_states, plot_state)
        elif lay["division"] == "each":
            colcount = 0
            for ds, sl in zip(dslist, slot_states):
                pp = PipelinePlotItem(parent=linner)
                linner.addItem(item=pp,
                               row=None,
                               col=None,
                               rowspan=1,
                               colspan=1)
                pp.redraw([ds], [sl], plot_state)
                colcount += 1
                if colcount % lay["column count"] == 0:
                    linner.nextRow()
        elif lay["division"] == "multiscatter+contour":
            colcount = 0
            # scatter plots
            plot_state_scatter = copy.deepcopy(plot_state)
            plot_state_scatter["contour"]["enabled"] = False
            for ds, sl in zip(dslist, slot_states):
                pp = PipelinePlotItem(parent=linner)
                linner.addItem(item=pp,
                               row=None,
                               col=None,
                               rowspan=1,
                               colspan=1)
                pp.redraw([ds], [sl], plot_state_scatter)
                colcount += 1
                if colcount % lay["column count"] == 0:
                    linner.nextRow()
            # contour plot
            plot_state_contour = copy.deepcopy(plot_state)
            plot_state_contour["scatter"]["enabled"] = False
            pp = PipelinePlotItem(parent=linner)
            linner.addItem(item=pp,
                           row=None,
                           col=None,
                           rowspan=1,
                           colspan=1)
            pp.redraw(dslist, slot_states, plot_state_contour)


class PipelinePlotItem(SimplePlotItem):
    def __init__(self, *args, **kwargs):
        super(PipelinePlotItem, self).__init__(*args, **kwargs)
        # Disable user interaction
        self.setMouseEnabled(x=False, y=False)
        # bring axes to front
        self.axes_to_front()
        # Keep track of all elements (for redraw)
        self._plot_elements = []

    def redraw(self, dslist, slot_states, plot_state):
        # Remove everything
        for el in self._plot_elements:
            self.removeItem(el)

        if not dslist:
            return

        # General
        gen = plot_state["general"]
        # TODO:
        # - test whether all datasets have same channel width / pixel size
        # Isoelastics
        if gen["isoelastics"]:
            cfg = dslist[0].config
            els = add_isoelastics(plot_item=self,
                                  axis_x=gen["axis x"],
                                  axis_y=gen["axis y"],
                                  channel_width=cfg["setup"]["channel width"],
                                  pixel_size=cfg["imaging"]["pixel size"])
            self._plot_elements += els
        # Set Range
        self.setRange(xRange=gen["range x"],
                      yRange=gen["range y"],
                      padding=0,
                      )
        # Set Log scale
        self.setLogMode(x=gen["scale x"] == "log",
                        y=gen["scale y"] == "log")
        # Scatter data
        if plot_state["scatter"]["enabled"]:
            for rtdc_ds, ss in zip(dslist, slot_states):
                sct = add_scatter(plot_item=self,
                                  rtdc_ds=rtdc_ds,
                                  plot_state=plot_state,
                                  slot_state=ss
                                  )
                self._plot_elements += sct
        # Contour data
        if plot_state["contour"]["enabled"]:
            # show legend
            if plot_state["contour"]["legend"]:
                legend = self.addLegend(offset=(-.01, +.01))
            else:
                legend = None
            for rtdc_ds, ss in zip(dslist, slot_states):
                con = add_contour(plot_item=self,
                                  rtdc_ds=rtdc_ds,
                                  plot_state=plot_state,
                                  slot_state=ss,
                                  legend=legend,
                                  )
                self._plot_elements += con

        # Set subplot title and number of events
        if plot_state["layout"]["label plots"]:
            if len(dslist) == 1 and plot_state["scatter"]["enabled"]:
                # only one scatter plot
                # set title
                ss = slot_states[0]
                thtmls = "<span style='color:{}'>{}</span>"
                title = thtmls.format(ss["color"], ss["name"])
                self.setTitle(title)
                if plot_state["scatter"]["show event count"]:
                    # set event count
                    chtml = "<span style='font-size:{}pt'>".format(
                        # default font size - 1
                        QtGui.QFont().pointSize() - 1) + "{} events</span>"
                    label = QtWidgets.QGraphicsTextItem(
                        "",
                        # This is kind of hackish: set the parent to the right
                        # axis so that it is always drawn there.
                        parent=self.axes["right"]["item"])
                    label.setHtml(chtml.format(len(sct[0].data)))
                    # move the label to the left by its width
                    label.setPos(-label.boundingRect().width()+2, -5)

            elif (plot_state["contour"]["enabled"]
                    and not plot_state["scatter"]["enabled"]):
                # only a contour plot
                # set title
                self.setTitle("Contours")


def add_contour(plot_item, plot_state, rtdc_ds, slot_state, legend=None):
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
            plot_item.addItem(cline)
            if ii == 0 and legend is not None:
                legend.addItem(cline, slot_state["name"])
            # Always plot higher percentiles above lower percentiles
            # (useful if there are multiple contour plots overlapping)
            cline.setZValue(con["percentiles"][ii])
    return elements


def add_isoelastics(plot_item, axis_x, axis_y, channel_width, pixel_size):
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
            plot_item.addItem(iline)
            elements.append(iline)
            # send them to the back
            iline.setZValue(-100)
    return elements


def add_scatter(plot_item, plot_state, rtdc_ds, slot_state):
    gen = plot_state["general"]
    sca = plot_state["scatter"]
    scatter = pg.ScatterPlotItem(size=sca["marker size"],
                                 pen=pg.mkPen(color=(0, 0, 0, 0)),
                                 brush=pg.mkBrush("k"),
                                 symbol="s")
    plot_item.addItem(scatter)

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
        alpha = int(sca["marker alpha"] * 255)
        color = pg.mkColor(slot_state["color"])
        color.setAlpha(alpha)
        brush = pg.mkBrush(color)
    else:
        alpha = int(sca["marker alpha"] * 255)
        color = pg.mkColor("k")
        color.setAlpha(alpha)
        brush = pg.mkBrush(color)

    # convert to log-scale if applicable
    if gen["scale x"] == "log":
        x = np.log10(x)
    if gen["scale y"] == "log":
        y = np.log10(y)

    scatter.setData(x=x, y=y, brush=brush)
    scatter.setZValue(-50)
    return [scatter]


def get_axes_labels(plot_state, slot_states):
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
    return labelx, labely


linestyles = {
    "solid": QtCore.Qt.SolidLine,
    "dashed": QtCore.Qt.DashLine,
    "dotted": QtCore.Qt.DotLine,
}
