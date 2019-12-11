import numbers
import pathlib
import pkg_resources

import numpy as np
from PyQt5 import QtWidgets


class KeyValueTableWidget(QtWidgets.QTableWidget):
    def __init__(self, *args, **kwargs):
        """A table widgets with two columns for key-value visualization"""
        super(KeyValueTableWidget, self).__init__(*args, **kwargs)
        path_css = pkg_resources.resource_filename(
            "shapeout2.gui.widgets", "key_value_table_widget.css")
        stylesheet = pathlib.Path(path_css).read_text()
        self.setStyleSheet(stylesheet)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setAlternatingRowColors(True)
        # For some reason this does not work here.
        # self.setColumnCount(2)
        # header = self.horizontalHeader()
        # header.setSectionResizeMode(0,
        #                             QtWidgets.QHeaderView.ResizeToContents)
        # header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

    def set_key_vals(self, keys, vals, max_key_len=23):
        """Convenience function for setting key-value pairs in this table"""
        # disable updates
        self.setUpdatesEnabled(False)
        # rows'n'cols
        self.setRowCount(len(keys))
        self.setColumnCount(2)
        # populate
        for ii, (hi, vi) in enumerate(zip(keys, vals)):
            # name
            if len(hi) < max_key_len:
                name_vis = hi
            else:
                name_vis = hi[:max_key_len-3] + "..."
            # pad with spaces (b/c css padding caused overlap)
            name_vis = " " + name_vis + " "
            label_name = self.cellWidget(ii, 0)
            if label_name is None:
                label_name = QtWidgets.QLabel(name_vis)
                self.setCellWidget(ii, 0, label_name)
            else:
                if label_name.text() != name_vis:
                    label_name.setText(name_vis)
            label_name.setToolTip(hi)
            # value
            if np.isnan(vi) or np.isinf(vi):
                fmt = "{}"
            elif isinstance(vi, numbers.Integral):
                fmt = "{}"
            elif vi == 0:
                fmt = "{:.1f}"
            else:
                dec = -int(np.ceil(np.log(np.abs(vi)))) + 3
                if dec <= 0:
                    dec = 1
                fmt = "{:." + "{}".format(dec) + "f}"
            value_vis = fmt.format(vi)
            label_value = self.cellWidget(ii, 1)
            if label_value is None:
                label_value = QtWidgets.QLabel(value_vis)
                self.setCellWidget(ii, 1, label_value)
            else:
                label_value.setText(value_vis)
            label_value.setToolTip(hi)
        # spacing (did not work in __init__)
        header = self.horizontalHeader()
        header.setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        # enable updates again
        self.setUpdatesEnabled(True)
