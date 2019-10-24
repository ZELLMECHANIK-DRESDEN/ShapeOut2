import pkg_resources

import dclab
from PyQt5 import uic, QtCore, QtWidgets

from ..pipeline import Plot
from ..pipeline.plot import STATE_OPTIONS


COLORMAPS = ["jet"]


class PlotPanel(QtWidgets.QWidget):
    #: Emitted when a shapeout2.pipeline.Plot is modified
    plots_changed = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "ana_plot.ui")
        uic.loadUi(path_ui, self)

        self.pushButton_reset.clicked.connect(self.update_content)
        self.pushButton_apply.clicked.connect(self.write_plot)
        self.comboBox_plots.currentIndexChanged.connect(self.update_content)
        self.comboBox_marker_hue.currentIndexChanged.connect(
            self.on_hue_select)

        # current Shape-Out 2 pipeline
        self._pipeline = None
        self._init_controls()
        self.update_content()

    def __getstate__(self):
        feats_srt = self.pipeline.get_features(label_sort=True)

        state = {
            "general": {
                "axis x": feats_srt[self.comboBox_axis_x.currentIndex()],
                "axis y": feats_srt[self.comboBox_axis_y.currentIndex()],
                "event count": self.checkBox_event_count.isChecked(),
                "isoelastics": self.checkBox_isoelastics.isChecked(),
                "kde": self.comboBox_kde.currentData(),
                "legend":  self.checkBox_legend.isChecked(),
                "name": self.lineEdit.text(),
                "scale x": self.comboBox_scale_x.currentData(),
                "scale y": self.comboBox_scale_y.currentData(),
                "size x": self.spinBox_size_x.value(),
                "size y": self.spinBox_size_y.value(),
            },
            "scatter": {
                "downsampling": self.checkBox_downsample.isChecked(),
                "downsampling value": self.spinBox_downsample.value(),
                "enabled": self.groupBox_scatter.isChecked(),
                "marker hue": self.comboBox_marker_hue.currentData(),
                "marker size": self.spinBox_marker_size.value(),
                "hue feature": self.comboBox_marker_feature.currentData(),
                "colormap": self.comboBox_colormap.currentData(),
            },
            "contour": {
                "enabled": self.groupBox_contour.isChecked(),
                "percentiles": [self.doubleSpinBox_perc_1.value(),
                                self.doubleSpinBox_perc_2.value(),
                                ],
                "line widths": [self.doubleSpinBox_lw_1.value(),
                                self.doubleSpinBox_lw_2.value(),
                                ],
                "line styles": [self.comboBox_ls_1.currentData(),
                                self.comboBox_ls_2.currentData(),
                                ],
                "spacing x": self.doubleSpinBox_spacing_x.value(),
                "spacing y": self.doubleSpinBox_spacing_y.value(),
            }
        }
        return state

    def __setstate__(self, state):
        feats_srt = self.pipeline.get_features(label_sort=True)

        # General
        gen = state["general"]
        self.comboBox_axis_x.setCurrentIndex(feats_srt.index(gen["axis x"]))
        self.comboBox_axis_y.setCurrentIndex(feats_srt.index(gen["axis y"]))
        self.checkBox_event_count.setChecked(gen["event count"])
        self.checkBox_isoelastics.setChecked(gen["isoelastics"])
        kde_index = self.comboBox_kde.findData(gen["kde"])
        self.comboBox_kde.setCurrentIndex(kde_index)
        self.checkBox_legend.setChecked(gen["legend"])
        self.lineEdit.setText(gen["name"])
        scx_index = self.comboBox_scale_x.findData(gen["scale x"])
        self.comboBox_scale_x.setCurrentIndex(scx_index)
        scy_index = self.comboBox_scale_y.findData(gen["scale y"])
        self.comboBox_scale_y.setCurrentIndex(scy_index)
        self.spinBox_size_x.setValue(gen["size x"])
        self.spinBox_size_y.setValue(gen["size y"])

        # Scatter
        sca = state["scatter"]
        self.checkBox_downsample.setChecked(sca["downsampling"])
        self.spinBox_downsample.setValue(sca["downsampling value"])
        self.groupBox_scatter.setChecked(sca["enabled"])
        hue_index = self.comboBox_marker_hue.findData(sca["marker hue"])
        self.comboBox_marker_hue.setCurrentIndex(hue_index)
        self.spinBox_marker_size.setValue(sca["marker size"])
        feat_index = feats_srt.index(sca["hue feature"])
        self.comboBox_marker_feature.setCurrentIndex(feat_index)
        color_index = COLORMAPS.index(sca["colormap"])
        self.comboBox_colormap.setCurrentIndex(color_index)

        # Contour
        con = state["contour"]
        self.groupBox_scatter.setChecked(con["enabled"])
        self.doubleSpinBox_perc_1.setValue(con["percentiles"][0])
        self.doubleSpinBox_perc_2.setValue(con["percentiles"][1])
        self.doubleSpinBox_lw_1.setValue(con["line widths"][0])
        self.doubleSpinBox_lw_2.setValue(con["line widths"][1])
        ls1_index = self.comboBox_ls_1.findData(con["line styles"][0])
        self.comboBox_ls_1.setCurrentIndex(ls1_index)
        ls2_index = self.comboBox_ls_2.findData(con["line styles"][1])
        self.comboBox_ls_2.setCurrentIndex(ls2_index)
        self.doubleSpinBox_spacing_x.setValue(con["spacing x"])
        self.doubleSpinBox_spacing_y.setValue(con["spacing y"])

    def _init_controls(self):
        """All controls that are not subject to change"""
        # KDE
        kde_names = STATE_OPTIONS["general"]["kde"]
        self.comboBox_kde.clear()
        for kn in kde_names:
            self.comboBox_kde.addItem(kn.capitalize(), kn)
        # Scales
        scales = STATE_OPTIONS["general"]["scale x"]
        self.comboBox_scale_x.clear()
        self.comboBox_scale_y.clear()
        for sc in scales:
            self.comboBox_scale_x.addItem(sc, sc)
            self.comboBox_scale_y.addItem(sc, sc)
        # Marker hue
        hues = STATE_OPTIONS["scatter"]["marker hue"]
        self.comboBox_marker_hue.clear()
        for hue in hues:
            if hue == "kde":
                huev = "KDE"
            else:
                huev = hue.capitalize()
            self.comboBox_marker_hue.addItem(huev, hue)
        self.comboBox_colormap.clear()
        for c in COLORMAPS:
            self.comboBox_colormap.addItem(c, c)
        # Contour line styles
        lstyles = STATE_OPTIONS["contour"]["line styles"][0]
        self.comboBox_ls_1.clear()
        self.comboBox_ls_2.clear()
        for l in lstyles:
            self.comboBox_ls_1.addItem(l, l)
            self.comboBox_ls_2.addItem(l, l)

    @property
    def current_plot(self):
        if self.plot_ids:
            plot_index = self.comboBox_plots.currentIndex()
            plot_id = self.ploter_ids[plot_index]
            plot = Plot.get_instances()[plot_id]
        else:
            plot = None
        return plot

    @property
    def pipeline(self):
        return self._pipeline

    @property
    def plot_ids(self):
        """List of plot names"""
        return sorted(Plot.get_instances().keys())

    @property
    def plot_names(self):
        """List of plot names"""
        return [Plot._instances[f].name for f in self.plot_ids]

    def on_hue_select(self):
        """Show/hide options for feature-based hue selection"""
        # Only show feature selection if needed
        if self.comboBox_marker_hue.currentData() == "feature":
            self.comboBox_marker_feature.show()
        else:
            self.comboBox_marker_feature.hide()
        # Only show colormap selection if needed
        if self.comboBox_marker_hue.currentData() in ["dataset", "none"]:
            self.comboBox_colormap.hide()
            self.label_colormap.hide()
        else:
            self.comboBox_colormap.show()
            self.label_colormap.show()

    def show_plot(self, plot_id):
        self.update_content(plot_index=self.plot_ids.index(plot_id))

    def set_pipeline(self, pipeline):
        self._pipeline = pipeline

    def update_content(self, event=None, plot_index=None):
        if self.plot_ids:
            self.setEnabled(True)
            # update combobox
            self.comboBox_plots.blockSignals(True)
            # this also updates the combobox
            if plot_index is None:
                plot_index = self.comboBox_plots.currentIndex()
                if plot_index > len(self.plot_ids) - 1 or plot_index < 0:
                    plot_index = len(self.plot_ids) - 1
            self.comboBox_plots.clear()
            self.comboBox_plots.addItems(self.plot_names)
            self.comboBox_plots.setCurrentIndex(plot_index)
            self.comboBox_plots.blockSignals(False)
            # set choices for all comboboxes that deal with features
            for cb in [self.comboBox_axis_x,
                       self.comboBox_axis_y,
                       self.comboBox_marker_feature]:
                if cb.count:
                    # remember current selection
                    curfeat = cb.currentData()
                else:
                    curfeat = None
                # repopulate
                cb.clear()
                feats_srt = self.pipeline.get_features(label_sort=True)
                for feat in feats_srt:
                    cb.addItem(dclab.dfn.feature_name2label[feat], feat)
                if curfeat is not None:
                    # write back current selection
                    curidx = feats_srt.index(curfeat)
                    cb.setCurrentIndex(curidx)
            # populate content
            plot = Plot.get_plot(identifier=self.plot_ids[plot_index])
            state = plot.__getstate__()
            self.__setstate__(state)
        else:
            self.setEnabled(False)

    def write_plot(self):
        """Update the shapeout2.pipeline.Plot instance"""
        # get current index
        filt_index = self.comboBox_plots.currentIndex()
        filt = Plot.get_plot(identifier=self.plot_names[filt_index])
        state = self.__getstate__()
        filt.__setstate__(state)
        self.plots_changed.emit()
