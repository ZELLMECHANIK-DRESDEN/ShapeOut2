import dclab
from PyQt5 import QtCore, QtGui, QtWidgets


class FeatureComboBox(QtWidgets.QComboBox):
    def __init__(self, *args, **kwargs):
        """A DC data aware combobox for displaying DC features

        The combobox uses different colors do indicate the
        availability of features. Features can be ancillary,
        innate, basin-based, etc.
        """
        super(FeatureComboBox, self).__init__(*args, **kwargs)
        self.rtdc_ds = None

        # where the data at
        self.data_role = QtCore.Qt.UserRole + 47

        # Set background color to white
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QtGui.QColor(255, 255, 255))

    def currentData(self, role=None):
        if role is None:
            role = self.data_role
        return super(FeatureComboBox, self).currentData(role)

    def findData(self, data, role=None):
        if role is None:
            role = self.data_role
        return super(FeatureComboBox, self).findData(data, role=role)

    def set_dataset(self, rtdc_ds, default_choice=None):
        self.rtdc_ds = rtdc_ds
        self.update_feature_list(default_choice=default_choice)

    @QtCore.pyqtSlot()
    def update_feature_list(self, default_choice=None):
        """Update the colors of all features in the combobox"""
        if self.rtdc_ds is None:
            raise ValueError("Please call `set_dataset` first!")
        # axes combobox choices
        ds_feats = self.rtdc_ds.features_scalar
        ds_labels = [dclab.dfn.get_feature_label(f) for f in ds_feats]
        ds_colors = []
        ds_tips = []
        feats_loaded = self.rtdc_ds.features_loaded
        feats_ancillary = self.rtdc_ds.features_ancillary
        feats_basin = self.rtdc_ds.features_basin
        for feat in ds_feats:
            if feat in feats_loaded:
                ds_colors.append("#D2FFC8")
                ds_tips.append("feature data loaded")
            elif feat in feats_basin:
                ds_colors.append("#C0E8FF")
                ds_tips.append("feature data located in basin")
            elif feat in feats_ancillary:
                ds_colors.append("#FFCACA")
                ds_tips.append("feature data needs to be computed")
            else:
                # fall-back
                ds_colors.append("#A9A9A9")
                ds_tips.append("unknown location of feature data")

        ds_fl = sorted(zip(ds_labels, ds_feats, ds_colors, ds_tips))

        feat_cur = self.currentData() or default_choice  # current selection
        blocked = self.signalsBlocked()  # remember block state
        self.blockSignals(True)

        # set features
        self.clear()
        model = self.model()
        for ii, (label, feat, color, tip) in enumerate(ds_fl):
            item = QtGui.QStandardItem(label)
            item.setData(feat, self.data_role)
            item.setBackground(QtGui.QColor(color))
            item.setForeground(QtGui.QColor("black"))
            item.setToolTip(tip)
            model.appendRow(item)

        # set previous selection
        idx_cur = self.findData(feat_cur)
        if idx_cur >= 0:
            self.setCurrentIndex(idx_cur)
        self.blockSignals(blocked)
