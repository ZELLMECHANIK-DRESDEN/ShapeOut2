import dclab
from PyQt5 import QtCore, QtWidgets


class FeatureComboBox(QtWidgets.QComboBox):
    def __init__(self, *args, **kwargs):
        """A DC data aware combobox for displaying DC features

        The combobox uses different colors do indicate the
        availability of features. Features can be ancillary,
        innate, basin-based, etc.
        """
        super(FeatureComboBox, self).__init__(*args, **kwargs)
        self.rtdc_ds = None

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
        ds_fl = sorted(zip(ds_labels, ds_feats))

        feat_cur = self.currentData() or default_choice  # current selection
        blocked = self.signalsBlocked()  # remember block state
        self.blockSignals(True)

        # set features
        self.clear()
        for label, feat in ds_fl:
            if feat in ds_feats:
                self.addItem(label, feat)

        # set previous selection
        idx_cur = self.findData(feat_cur)
        if idx_cur >= 0:
            self.setCurrentIndex(idx_cur)
        self.blockSignals(blocked)
