import pkg_resources

import numpy as np
from PyQt5 import uic, QtCore, QtWidgets


class RangeControl(QtWidgets.QWidget):
    def __init__(self, parent, label="feature", checkbox=True, integer=False,
                 data=None, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent, *args, **kwargs)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "rangecontrol.ui")
        uic.loadUi(path_ui, self)

        # arbitrary data
        self.data = data

        # default values for limits
        self.minimum = -100
        self.maximum = +100

        # label on top of control
        self.setLabel(label)

        # enable/disable checkbox
        if not checkbox:
            self.checkBox.hide()

        # integer-valued control
        if integer:
            self.doubleSpinBox_min.setDecimals(0)
            self.doubleSpinBox_max.setDecimals(0)
        self.is_integer = integer

        # signals
        self.range_slider.rangeChanged.connect(self.on_range)
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
        self.doubleSpinBox_min.blockSignals(True)
        self.doubleSpinBox_max.blockSignals(True)
        self.doubleSpinBox_min.setValue(state["start"])
        self.doubleSpinBox_max.setValue(state["end"])
        self.doubleSpinBox_min.blockSignals(False)
        self.doubleSpinBox_max.blockSignals(False)
        self.map_spin_values_to_range_slider()

    @QtCore.pyqtSlot(float, float)
    def map_spin_values_to_range_slider(self, vmin=None, vmax=None):
        # limits
        lmin = self.minimum
        lmax = self.maximum
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
        if dl * dr == 0:
            hmin = hmax = 0
        else:
            hmin = rmin + (vmin - lmin) / dl * dr
            hmax = rmax - (lmax - vmax) / dl * dr
        if hmin < rmin:
            hmin = 0
        if hmax > rmax:
            hmax = self.range_slider._INT_NUM
        self.range_slider.blockSignals(True)
        self.range_slider.setRange(hmin, hmax)
        self.range_slider.blockSignals(False)
        # make range selection stick tight to edges
        if hmin < 10:
            hmin = 0
        if hmin > self.range_slider._INT_NUM - 10:
            hmax = self.range_slider._INT_NUM
        return hmin, hmax

    @QtCore.pyqtSlot(int, int)
    def map_range_slider_to_spin_values(self, hmin=None, hmax=None):
        """Return the respective value of the current range

        Range limits are defined by
        - self.doubleSpinBox_min.minimum()
        - self.doubleSpinBox_min.maximum()
        """
        # limits
        lmin = self.minimum
        lmax = self.maximum
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
        self.doubleSpinBox_max.blockSignals(True)
        self.doubleSpinBox_min.setValue(vmin)
        self.doubleSpinBox_max.setValue(vmax)
        self.doubleSpinBox_min.blockSignals(False)
        self.doubleSpinBox_max.blockSignals(False)
        return vmin, vmax

    def on_range(self):
        self.map_range_slider_to_spin_values()

    def on_spinbox(self):
        self.map_spin_values_to_range_slider()

    def reset_range(self):
        self.doubleSpinBox_min.setValue(self.minimum)
        self.doubleSpinBox_max.setValue(self.maximum)

    def setCheckable(self, b=True):
        self.checkBox.setVisible(b)

    def setInteger(self, b=True):
        self.is_integer = b

    def setLabel(self, label):
        if label:
            self.label.setText(label)
            self.label.show()
        else:
            self.label.hide()

    def setLimits(self, vmin, vmax, hard_limit=False):
        """Set the limits of the range control

        Parameters
        ----------
        vmin, vmax: float
            Minimum and maximum values
        hard_limit: bool
            If set to True, the spin controls will have a hard limit
            that matches vmin and vmax. If False (default), the
            limit of the spin controls is larger, giving the user
            a broader range.
        """
        self.minimum = vmin
        self.maximum = vmax

        if hard_limit:
            vminh = vmin
            vmaxh = vmax
        else:
            # estimate based on number of digits
            if vmin >= 0:
                vminh = 0
            else:
                lmin = np.int(np.ceil(np.log10(np.abs(vmin)))) + 1
                vminh = -10**lmin
            if vmax > 0:
                lmax = np.int(np.ceil(np.log10(vmax))) + 1
                vmaxh = 10**lmax
            else:
                vmax = 0

        self.setSpinLimits(vmin=vminh, vmax=vmaxh)
        # slider values
        self.map_spin_values_to_range_slider()

    def setSpinLimits(self, vmin, vmax):
        """Only sets spin control limits"""
        # min/max
        self.doubleSpinBox_min.setMinimum(vmin)
        self.doubleSpinBox_max.setMinimum(vmin)
        self.doubleSpinBox_min.setMaximum(vmax)
        self.doubleSpinBox_max.setMaximum(vmax)

        # decimals
        if not self.is_integer:
            # two significant digits
            dec = -int(np.ceil(np.log10(vmax-vmin))) + 4
            if dec <= 0:
                dec = 1
            self.doubleSpinBox_min.setDecimals(dec)
            self.doubleSpinBox_max.setDecimals(dec)
            self.doubleSpinBox_min.setSingleStep(10**-dec)
            self.doubleSpinBox_max.setSingleStep(10**-dec)
