import pkg_resources

from PyQt5 import uic, QtWidgets

import dclab

from ..filter import Filter

from . import rangecontrol


# integer-valued features
INT_FEATURES = [
    "fl1_max",
    "fl1_npeaks",
    "fl2_max",
    "fl2_npeaks",
    "fl3_max",
    "fl3_npeaks",
    "frame",
    "index",
    "nevents",
]

# features shown by default
SHOW_FEATURES = ["deform", "area_um", "index"]


class FilterPanel(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "ana_filter.ui")
        uic.loadUi(path_ui, self)

        self._init_box_filters()

        self.pushButton_update.clicked.connect(self.write_filter)
        self.pushButton_reset.clicked.connect(self.update_content)
        self.comboBox_filters.currentIndexChanged.connect(self.update_content)

        self.update_content()

    def _init_box_filters(self, show_features=SHOW_FEATURES):
        self._box_range_controls = {}
        for feat in dclab.dfn.scalar_feature_names:
            integer = True if feat in INT_FEATURES else False
            rc = rangecontrol.RangeControl(
                checkbox=True,
                integer=integer,
                label=dclab.dfn.feature_name2label[feat],
                data=feat)
            self.verticalLayout_box.addWidget(rc)
            if feat not in show_features:
                rc.hide()
            self._box_range_controls[feat] = rc

    @property
    def current_filter(self):
        if self.filter_names:
            filt_index = self.comboBox_filters.currentIndex()
            filt_name = self.filter_names[filt_index]
            filt = Filter.get_instances()[filt_name]
        else:
            filt = None
        return filt

    @property
    def filter_names(self):
        """List of filter names"""
        return sorted(Filter.get_instances().keys())

    @property
    def visible_box_features(self):
        """List of box-filtered features that are visible"""
        vis = []
        for feat in self._box_range_controls:
            if not self._box_range_controls[feat].isHidden():
                vis.append(feat)
        return vis

    def set_filter_state(self, state):
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
            elif not rc.isHidden():
                # update range to limits
                rc.reset_range()

    def get_filter_state(self):
        state = {
            "enable filters": self.checkBox_enable.isChecked(),
            "name": self.lineEdit_name.text(),
            "limit events bool": self.checkBox_limit.isChecked(),
            "limit events num": self.spinBox_limit.value(),
            "remove invalid events": self.checkBox_invalid.isChecked(),
        }
        # box filters
        box = {}
        for feat in self._box_range_controls:
            rc = self._box_range_controls[feat]
            if rc.isVisible():
                box[feat] = rc.__getstate__()
        state["box filters"] = box
        return state

    def show_filter(self, filt_id):
        self.update_content(filt_index=self.filter_names.index(filt_id))

    def update_content(self, event=None, filt_index=None):
        if self.filter_names:
            self.setEnabled(True)
            # update combobox
            self.comboBox_filters.blockSignals(True)
            # this also updates the combobox
            if filt_index is None:
                filt_index = self.comboBox_filters.currentIndex()
                if filt_index > len(self.filter_names) - 1 or filt_index < 0:
                    filt_index = len(self.filter_names) - 1
            self.comboBox_filters.clear()
            self.comboBox_filters.addItems(self.filter_names)
            self.comboBox_filters.setCurrentIndex(filt_index)
            self.comboBox_filters.blockSignals(False)
            # populate content
            filt = Filter.get_filter(identifier=self.filter_names[filt_index])
            state = filt.__getstate__()
            self.set_filter_state(state)
            self.update_box_filters()
        else:
            self.setEnabled(False)

    def update_box_filters(self, show_features=None, mmdict={}):
        """Update the box plot filters

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
        # update used features
        for feat in self._box_range_controls:
            rc = self._box_range_controls[feat]
            if show_features is not None:
                rc.setVisible(feat in show_features)
            if feat in mmdict:
                rc.setLimits(*mmdict[feat])
            if self.current_filter is not None:
                state = self.current_filter.__getstate__()
                if feat not in state["box filters"]:
                    # reset range to limits
                    rc.reset_range()

    def write_filter(self):
        """Update the shapeout2.filter.Filter instance"""
        # get current index
        filt_index = self.comboBox_filters.currentIndex()
        filt = Filter.get_filter(identifier=self.filter_names[filt_index])
        state = self.get_filter_state()
        filt.__setstate__(state)
