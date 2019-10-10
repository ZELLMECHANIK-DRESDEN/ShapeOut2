import pkg_resources

from PyQt5 import uic, QtWidgets

from ..filter import Filter


class FilterPanel(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui", "ana_filter.ui")
        uic.loadUi(path_ui, self)

        self.update_content()
        self.pushButton_update.clicked.connect(self.update_filter)
        self.pushButton_reset.clicked.connect(self.update_content)
        self.comboBox_filters.currentIndexChanged.connect(self.update_content)

    @property
    def filters(self):
        """List of filters"""
        return sorted(Filter.get_instances().keys())

    def set_filter_state(self, state):
        self.checkBox_enable.setChecked(state["enable filters"])
        self.lineEdit_name.setText(state["name"])
        self.checkBox_limit.setChecked(state["limit events bool"])
        self.spinBox_limit.setValue(state["limit events num"])
        self.checkBox_invalid.setChecked(state["remove invalid events"])

    def get_filter_state(self):
        state = {
            "enable filters": self.checkBox_enable.isChecked(),
            "name": self.lineEdit_name.text(),
            "limit events bool": self.checkBox_limit.isChecked(),
            "limit events num": self.spinBox_limit.value(),
            "remove invalid events": self.checkBox_invalid.isChecked(),
        }
        return state

    def show_filter(self, filt_id):
        self.update_content(filt_index=self.filters.index(filt_id))

    def update_content(self, event=None, filt_index=None):
        if self.filters:
            self.setEnabled(True)
            # update combobox
            self.comboBox_filters.blockSignals(True)
            if filt_index is None:
                filt_index = self.comboBox_filters.currentIndex()
                if filt_index > len(self.filters) - 1 or filt_index < 0:
                    filt_index = len(self.filters) - 1
            self.comboBox_filters.clear()
            self.comboBox_filters.addItems(self.filters)
            self.comboBox_filters.setCurrentIndex(filt_index)
            self.comboBox_filters.blockSignals(False)
            # populate content
            filt = Filter.get_filter(identifier=self.filters[filt_index])
            state = filt.__getstate__()
            self.set_filter_state(state)
        else:
            self.setEnabled(False)

    def update_filter(self):
        """Update the shapeout2.filter.Filter instance"""
        # get current index
        filt_index = self.comboBox_filters.currentIndex()
        filt = Filter.get_filter(identifier=self.filters[filt_index])
        state = self.get_filter_state()
        filt.__setstate__(state)
