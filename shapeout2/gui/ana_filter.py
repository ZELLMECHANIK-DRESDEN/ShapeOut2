import pkg_resources

from PyQt5 import uic, QtCore, QtWidgets

import dclab

from ..pipeline import Filter

from . import rangecontrol
from . import idiom

# features shown by default
SHOW_FEATURES = ["deform", "area_um", "bright_avg"]


class FilterPanel(QtWidgets.QWidget):
    #: Emitted when a shapeout2.filter.Filter modified
    filters_changed = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "ana_filter.ui")
        uic.loadUi(path_ui, self)

        self._init_box_filters()

        self.pushButton_apply.clicked.connect(self.write_filter)
        self.pushButton_reset.clicked.connect(self.update_content)
        self.comboBox_filters.currentIndexChanged.connect(self.update_content)
        self.toolButton_moreless.clicked.connect(self.on_moreless)
        self._box_edit_view = False
        self.update_content()
        # current Shape-Out 2 pipeline
        self._pipeline = None

    def _init_box_filters(self, show_features=SHOW_FEATURES):
        self._box_range_controls = {}
        feats = dclab.dfn.scalar_feature_names
        labs = [dclab.dfn.feature_name2label[f] for f in feats]

        for lab, feat in sorted(zip(labs, feats)):
            integer = True if feat in idiom.INTEGER_FEATURES else False
            rc = rangecontrol.RangeControl(
                checkbox=False,  # checkbox is used in on_moreless
                integer=integer,
                label=lab,
                data=feat)
            self.verticalLayout_box.addWidget(rc)
            if feat not in show_features:
                rc.checkBox.setChecked(False)
                rc.setVisible(False)
            self._box_range_controls[feat] = rc

    def __getstate__(self):
        state = {
            "enable filters": self.checkBox_enable.isChecked(),
            "name": self.lineEdit_name.text(),
            "limit events bool": self.checkBox_limit.isChecked(),
            "limit events num": self.spinBox_limit.value(),
            "remove invalid events": self.checkBox_invalid.isChecked(),
        }
        # box filters
        box = {}
        for feat in self.active_box_features:
            rc = self._box_range_controls[feat]
            box[feat] = rc.__getstate__()
        state["box filters"] = box
        return state

    def __setstate__(self, state):
        self.checkBox_enable.setChecked(state["enable filters"])
        self.lineEdit_name.setText(state["name"])
        self.checkBox_limit.setChecked(state["limit events bool"])
        self.spinBox_limit.setValue(state["limit events num"])
        self.checkBox_invalid.setChecked(state["remove invalid events"])
        # box filters
        box = state["box filters"]
        for feat in self._box_range_controls:
            rc = self._box_range_controls[feat]
            if feat in box:
                rc.show()
                rc.__setstate__(box[feat])
            elif not rc.isHidden():
                # update range to limits
                rc.reset_range()

    @property
    def active_box_features(self):
        """List of box-filtered features that are active"""
        act = []
        for feat, item in self._box_range_controls.items():
            if item.__getstate__()["active"]:
                act.append(feat)
        return act

    @property
    def current_filter(self):
        if self.filter_ids:
            filt_index = self.comboBox_filters.currentIndex()
            filt_id = self.filter_ids[filt_index]
            filt = Filter.get_instances()[filt_id]
        else:
            filt = None
        return filt

    @property
    def filter_ids(self):
        """List of filter names"""
        return sorted(Filter.get_instances().keys())

    @property
    def filter_names(self):
        """List of filter names"""
        return [Filter._instances[f].name for f in self.filter_ids]

    @property
    def pipeline(self):
        return self._pipeline

    def on_moreless(self):
        """User wants to choose box filters"""
        if not self._box_edit_view:
            # Show all filters to the user
            for _, rc in self._box_range_controls.items():
                rc.setVisible(True)
                rc.checkBox.setVisible(True)
                rc.doubleSpinBox_min.setEnabled(False)
                rc.doubleSpinBox_max.setEnabled(False)
                rc.range_slider.setEnabled(False)
            self.toolButton_moreless.setText("...Finish editing")
            self._box_edit_view = True
        else:
            # Hide all filters that are not active
            for _, rc in self._box_range_controls.items():
                if not rc.__getstate__()["active"]:
                    rc.setVisible(False)
                rc.checkBox.setVisible(False)
                rc.doubleSpinBox_min.setEnabled(True)
                rc.doubleSpinBox_max.setEnabled(True)
                rc.range_slider.setEnabled(True)
            self.toolButton_moreless.setText("Choose filters...")
            self._box_edit_view = False
            # Update box filter ranges
            self.update_box_ranges()

    def set_pipeline(self, pipeline):
        self._pipeline = pipeline

    def show_filter(self, filt_id):
        self.update_content(filt_index=self.filter_ids.index(filt_id))

    def update_content(self, event=None, filt_index=None):
        if self.filter_ids:
            self.setEnabled(True)
            # update combobox
            self.comboBox_filters.blockSignals(True)
            # this also updates the combobox
            if filt_index is None:
                filt_index = self.comboBox_filters.currentIndex()
                if filt_index > len(self.filter_ids) - 1 or filt_index < 0:
                    filt_index = len(self.filter_ids) - 1
            self.comboBox_filters.clear()
            self.comboBox_filters.addItems(self.filter_names)
            self.comboBox_filters.setCurrentIndex(filt_index)
            self.comboBox_filters.blockSignals(False)
            # populate content
            filt = Filter.get_filter(identifier=self.filter_ids[filt_index])
            state = filt.__getstate__()
            self.__setstate__(state)
            self.update_box_ranges()
        else:
            self.setEnabled(False)

    def update_box_ranges(self):
        """Update the box plot filter ranges

        Parameters
        ----------
        show_features: None or list of str
            The features to show. Features in this list will become
            visible, all other features will be hidden.
            If set to `None`, no changes are performed.
        mmdict: dict
            The min/max dictionary for updating the limits.
            Each key is a feature name; each item is a tuple
            of min/max values for that feature.
        """
        if self.pipeline is not None and self.pipeline.num_slots:
            # compute min/max values
            mmdict = {}
            for feat in self.active_box_features:
                mmdict[feat] = self.pipeline.get_min_max(feat=feat)
            # update used features
            for feat in self._box_range_controls:
                rc = self._box_range_controls[feat]
                if feat in mmdict:
                    rc.setLimits(*mmdict[feat])
                if self.current_filter is not None:
                    state = self.current_filter.__getstate__()
                    if feat not in state["box filters"]:
                        # reset range to limits
                        rc.reset_range()

    def write_filter(self):
        """Update the shapeout2.pipeline.Filter instance"""
        # get current index
        filt_index = self.comboBox_filters.currentIndex()
        filt = Filter.get_filter(identifier=self.filter_names[filt_index])
        state = self.__getstate__()
        filt.__setstate__(state)
        self.filters_changed.emit()
