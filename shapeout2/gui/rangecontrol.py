import pkg_resources

import numpy as np
from PyQt5 import uic, QtCore, QtWidgets


class RangeControl(QtWidgets.QWidget):
    def __init__(self, label="feature", checkbox=True, integer=False,
                 data=None, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "rangecontrol.ui")
        uic.loadUi(path_ui, self)

        # arbitrary data
        self.data = data

        # label on top of control
        self.label.setText(label)

        # enable/disable checkbox
        if not checkbox:
            self.checkBox.hide()

        # integer-valued control
        if integer:
            self.doubleSpinBox_min.setDecimals(0)
            self.doubleSpinBox_max.setDecimals(0)
        self.is_integer = integer

        # signals
        self.checkBox.clicked.connect(self.on_checkbox_enable_control)
        self.range_slider.rangeChanged.connect(
            self.map_range_slider_to_spin_values)
        self.doubleSpinBox_min.valueChanged.connect(self.on_spinbox)
        self.doubleSpinBox_max.valueChanged.connect(self.on_spinbox)

        # call show to make sure slider is updated
        self.show()

    def __getstate__(self):
        state = {
            "active": self.checkBox.isChecked(),
            "start": self.doubleSpinBox_min.value(),
            "end": self.doubleSpinBox_max.value(),
            }
        return state

    def __setstate__(self, state):
        self.checkBox.setChecked(state["active"])
        self.doubleSpinBox_min.setValue(state["start"])
        self.doubleSpinBox_max.setValue(state["end"])

    @QtCore.pyqtSlot(float, float)
    def map_spin_values_to_range_slider(self, vmin=None, vmax=None):
        # limits
        lmin = self.doubleSpinBox_min.minimum()
        lmax = self.doubleSpinBox_min.maximum()
        # spin values
        if vmin is None:
            vmin = self.doubleSpinBox_min.value()
        if vmax is None:
            vmax = self.doubleSpinBox_max.value()
        # range slider limits
        rmin = self.range_slider.min()
        rmax = self.range_slider.max()
        # compute values
        dr = rmax - rmin
        dl = lmax - lmin
        hmin = rmin + (vmin - lmin) / dl * dr
        hmax = rmax - (lmax - vmax) / dl * dr

        self.range_slider.blockSignals(True)
        self.range_slider.setRange(hmin, hmax)
        self.range_slider.blockSignals(False)

        return hmin, hmax

    @QtCore.pyqtSlot(int, int)
    def map_range_slider_to_spin_values(self, hmin=None, hmax=None):
        """Return the respective value of the current range

        Range limits are defined by
        - self.doubleSpinBox_min.minimum()
        - self.doubleSpinBox_min.maximum()
        """
        # limits
        lmin = self.doubleSpinBox_min.minimum()
        lmax = self.doubleSpinBox_min.maximum()
        # range slider limits
        rmin = self.range_slider.min()
        rmax = self.range_slider.max()
        # range slider handles
        if hmin is None:
            hmin = self.range_slider.start()
        if hmax is None:
            hmax = self.range_slider.end()
        # compute values
        dr = rmax - rmin
        dl = lmax - lmin
        vmin = lmin + (hmin - rmin) / dr * dl
        vmax = lmax - (rmax - hmax) / dr * dl

        self.doubleSpinBox_min.blockSignals(True)
        self.doubleSpinBox_min.setValue(vmin)
        self.doubleSpinBox_min.blockSignals(False)

        self.doubleSpinBox_max.blockSignals(True)
        self.doubleSpinBox_max.setValue(vmax)
        self.doubleSpinBox_max.blockSignals(False)

        return vmin, vmax

    def on_checkbox_enable_control(self, enable=True):
        self.doubleSpinBox_min.setEnabled(enable)
        self.doubleSpinBox_max.setEnabled(enable)
        self.range_slider.setEnabled(enable)

    def on_spinbox(self):
        self.map_spin_values_to_range_slider()

    def reset_range(self):
        self.doubleSpinBox_min.setValue(self.doubleSpinBox_min.minimum())
        self.doubleSpinBox_max.setValue(self.doubleSpinBox_min.maximum())

    def setLimits(self, vmin, vmax):
        # min/max
        self.doubleSpinBox_min.setMinimum(vmin)
        self.doubleSpinBox_max.setMinimum(vmin)
        self.doubleSpinBox_min.setMaximum(vmax)
        self.doubleSpinBox_max.setMaximum(vmax)

        # decimals
        if not self.is_integer:
            # two significant digits
            dec = -int(np.ceil(np.log(vmax-vmin))) + 3
            if dec <= 0:
                dec = 1
            self.doubleSpinBox_min.setDecimals(dec)
            self.doubleSpinBox_max.setDecimals(dec)
            self.doubleSpinBox_min.setSingleStep(10**-dec)
            self.doubleSpinBox_max.setSingleStep(10**-dec)

        # slider values
        self.map_spin_values_to_range_slider()
