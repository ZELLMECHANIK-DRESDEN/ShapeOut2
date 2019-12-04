import copy
import pkg_resources

from PyQt5 import uic, QtCore, QtWidgets

import dclab

from ...pipeline import Filter

from .. import rangecontrol
from .. import idiom


class FilterPanel(QtWidgets.QWidget):
    #: Emitted when a shapeout2.pipeline.Filter is to be changed
    filter_changed = QtCore.pyqtSignal(dict)
    #: Emitted when the pipeline is to be changed
    pipeline_changed = QtCore.pyqtSignal(dict)
    #: Emitted when the user wants to create a new polygon filter
    request_new_polygon_filter = QtCore.pyqtSignal()

    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.analysis", "ana_filter.ui")
        uic.loadUi(path_ui, self)
        # current Shape-Out 2 pipeline
        self._pipeline = None
        self.setUpdatesEnabled(False)
        self._init_box_filters()
        self._polygon_checkboxes = {}
        self.update_polygon_filters()
        self.pushButton_duplicate.clicked.connect(self.on_duplicate_filter)
        self.pushButton_remove.clicked.connect(self.on_remove_filter)
        self.pushButton_apply.clicked.connect(self.write_filter)
        self.pushButton_reset.clicked.connect(self.update_content)
        self.comboBox_filters.currentIndexChanged.connect(self.update_content)
        self.toolButton_moreless.clicked.connect(self.on_moreless)
        self._box_edit_view = False
        self.update_content()
        self.setUpdatesEnabled(True)

    def __getstate__(self):
        state = {
            "filter used": self.checkBox_enable.isChecked(),
            "identifier": self.current_filter.identifier,
            "limit events bool": self.checkBox_limit.isChecked(),
            "limit events num": self.spinBox_limit.value(),
            "name": self.lineEdit_name.text(),
            "remove invalid events": self.checkBox_invalid.isChecked(),
        }
        # box filters
        box = {}
        for feat in self.active_box_features:
            rc = self._box_range_controls[feat]
            box[feat] = rc.__getstate__()
        state["box filters"] = box
        # polygon filters
        pflist = []
        for key in self._polygon_checkboxes:
            if self._polygon_checkboxes[key].isChecked():
                pflist.append(key)
        state["polygon filters"] = pflist
        return state

    def __setstate__(self, state):
        if self.current_filter.identifier != state["identifier"]:
            raise ValueError("Filter identifier mismatch!")
        self.checkBox_enable.setChecked(state["filter used"])
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
            else:
                rc.hide()
                rc.reset_range()

        # polygon filters
        pflist = state["polygon filters"]
        for key in self._polygon_checkboxes:
            if key in pflist:
                self._polygon_checkboxes[key].setChecked(True)
            else:
                self._polygon_checkboxes[key].setChecked(False)

    def _init_box_filters(self):
        self._box_range_controls = {}
        feats = dclab.dfn.scalar_feature_names
        labs = [dclab.dfn.feature_name2label[f] for f in feats]
        self.verticalLayout_box.setAlignment(QtCore.Qt.AlignTop)

        for lab, feat in sorted(zip(labs, feats)):
            integer = True if feat in idiom.INTEGER_FEATURES else False
            rc = rangecontrol.RangeControl(
                self,
                checkbox=False,  # checkbox is used in on_moreless
                integer=integer,
                label=lab,
                data=feat)
            rc.checkBox.setChecked(False)
            rc.setVisible(False)
            self.verticalLayout_box.addWidget(rc)
            self._box_range_controls[feat] = rc

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
        """List of filter identifiers"""
        if self.pipeline is not None:
            ids = [filt.identifier for filt in self.pipeline.filters]
        else:
            ids = []
        return ids

    @property
    def filter_names(self):
        """List of filter names"""
        if self.pipeline is not None:
            nms = [filt.name for filt in self.pipeline.filters]
        else:
            nms = []
        return nms

    @property
    def pipeline(self):
        return self._pipeline

    def on_duplicate_filter(self):
        # determine the new filter state
        filt_state = self.__getstate__()
        new_state = copy.deepcopy(filt_state)
        new_filt = Filter()
        new_state["identifier"] = new_filt.identifier
        new_state["name"] = new_filt.name
        new_filt.__setstate__(new_state)
        # determine the filter position
        pos = self.pipeline.filter_ids.index(filt_state["identifier"])
        self.pipeline.add_filter(new_filt, index=pos+1)
        state = self.pipeline.__getstate__()
        self.pipeline_changed.emit(state)

    def on_remove_filter(self):
        filt_state = self.__getstate__()
        self.pipeline.remove_filter(filt_state["identifier"])
        state = self.pipeline.__getstate__()
        self.pipeline_changed.emit(state)

    def on_moreless(self):
        """User wants to choose box filters"""
        features = self.pipeline.get_features(scalar=True,
                                              label_sort=True,
                                              union=True)
        if not self._box_edit_view:
            # Show all filters to the user
            for feat, rc in self._box_range_controls.items():
                if feat in features:
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
            self.update_polygon_filters(update_state=False)
            # update combobox
            self.comboBox_filters.blockSignals(True)
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

    def update_polygon_filters(self, update_state=True):
        """Update the layout containing the polygon filters"""
        self.verticalLayout_poly.setAlignment(QtCore.Qt.AlignTop)
        # clear layout
        for ii in reversed(range(self.verticalLayout_poly.count())):
            item = self.verticalLayout_poly.itemAt(ii).widget()
            if item is not None:
                item.deleteLater()
        self._polygon_checkboxes = {}  # must come after getting the state
        if dclab.PolygonFilter.instances:
            for pf in dclab.PolygonFilter.instances:
                widget = QtWidgets.QWidget()
                hbox = QtWidgets.QHBoxLayout()
                hbox.setAlignment(QtCore.Qt.AlignLeft)
                hbox.setContentsMargins(0, 0, 0, 0)
                chb = QtWidgets.QCheckBox()
                hbox.addWidget(chb)
                hbox.addWidget(QtWidgets.QLabel(pf.name))
                widget.setLayout(hbox)
                self.verticalLayout_poly.addWidget(widget)
                self._polygon_checkboxes[pf.unique_id] = chb
        else:
            label = QtWidgets.QLabel("No polygon filters have been created "
                                     + "yet.")
            button = QtWidgets.QPushButton("Create polygon filter")
            button.clicked.connect(self.request_new_polygon_filter)
            self.verticalLayout_poly.addWidget(label)
            self.verticalLayout_poly.addWidget(button)
        # update current filters
        if update_state and self.current_filter is not None:
            self.__setstate__(self.current_filter.__getstate__())

    def write_filter(self):
        """Update the shapeout2.pipeline.Filter instance"""
        # get current index
        filter_state = self.__getstate__()
        self.filter_changed.emit(filter_state)
        self.update_content()  # update filter selection combobox
