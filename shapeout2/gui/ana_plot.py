import pkg_resources

import dclab
from PyQt5 import uic, QtWidgets

from ..pipeline import Plot


class PlotPanel(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "ana_plot.ui")
        uic.loadUi(path_ui, self)

        self.pushButton_reset.clicked.connect(self.update_content)
        self.pushButton_apply.clicked.connect(self.write_plot)

        self.update_content()
        # current Shape-Out 2 pipeline
        self._pipeline = None

    def __getstate__(self):
        feats = self.pipeline.get_features()
        labs = [dclab.dfn.feature_name2label[f] for f in feats]
        lf = sorted(zip(labs, feats))
        feats_srt = [it[1] for it in lf]

        state = {
            "general": {
                "axis x": feats_srt[self.comboBox_axis_x.currentIndex()],
                "axis y": feats_srt[self.comboBox_axis_y.currentIndex()],
                "event count": True,  # display event count
                "isoelastics": True,  # display isoelasticity lines
                "kde": "histogram",  # see dclab.kde_methods.methods
                "legend": True,  # display plot legend
                "name": "no default",  # overridden by __init__
                "scale x": "linear",
                "scale y": "linear",
                "size x": float,
                "size y": float,
            },
            "scatter": {
                "downsampling": True,
                "downsampling value": 5000,
                "marker hue": "kde",
                "marker size": 1.0,
                "hue feature": "emodulus",
                "colormap": "jet",
            },
            "contour": {
                "percentiles": [50.0, 95.0],
                "line widths": [3.0, 1.5],
                "line styles": ["solid", "dashed"],
                "spacing x": 10,
                "spacing y": 0.01,
            }
        }
        return state

    def __setstate__(self, state):
        gen = state["general"]

        feats = self.pipeline.get_features()
        labs = [dclab.dfn.feature_name2label[f] for f in feats]
        lf = sorted(zip(labs, feats))
        feats_srt = [it[1] for it in lf]
        labs_srt = [it[0] for it in lf]
        self.comboBox_axis_x.clear()
        self.comboBox_axis_x.addItems(labs_srt)
        self.comboBox_axis_x.setCurrentIndex(feats_srt.index(gen["axis x"]))
        self.comboBox_axis_y.clear()
        self.comboBox_axis_y.addItems(labs_srt)
        self.comboBox_axis_y.setCurrentIndex(feats_srt.index(gen["axis y"]))

        state = {
            "general": {
                "event count": True,  # display event count
                "isoelastics": True,  # display isoelasticity lines
                "kde": "histogram",  # see dclab.kde_methods.methods
                "legend": True,  # display plot legend
                "name": "no default",  # overridden by __init__
                "scale x": "linear",
                "scale y": "linear",
                "size x": float,
                "size y": float,
            },
            "scatter": {
                "downsampling": True,
                "downsampling value": 5000,
                "marker hue": "kde",
                "marker size": 1.0,
                "hue feature": "emodulus",
                "colormap": "jet",
            },
            "contour": {
                "percentiles": [50.0, 95.0],
                "line widths": [3.0, 1.5],
                "line styles": ["solid", "dashed"],
                "spacing x": 10,
                "spacing y": 0.01,
            }
        }

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
        state = self.get_plot_state()
        filt.__setstate__(state)
        self.plots_changed.emit()
