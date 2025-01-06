import importlib.resources

from PyQt6 import uic, QtCore, QtWidgets


class AnalysisView(QtWidgets.QWidget):
    filter_changed = QtCore.pyqtSignal(dict)
    plot_changed = QtCore.pyqtSignal(dict)
    slot_changed = QtCore.pyqtSignal(dict)
    pipeline_changed = QtCore.pyqtSignal(dict)

    def __init__(self, *args, **kwargs):
        super(AnalysisView, self).__init__(*args, **kwargs)
        ref = importlib.resources.files(
            "shapeout2.gui.analysis") / "ana_view.ui"
        with importlib.resources.as_file(ref) as path_ui:
            uic.loadUi(path_ui, self)

        self.page_widgets = [
            self.widget_basins,
            self.widget_meta,
            self.widget_filter,
            self.widget_log,
            self.widget_meta,
            self.widget_plot,
            self.widget_slot,
            self.widget_tables
        ]

        self.setWindowTitle("Analysis View")
        self.setMinimumSize(self.sizeHint())
        # Signals
        self.widget_filter.filter_changed.connect(self.filter_changed)
        self.widget_filter.pipeline_changed.connect(self.pipeline_changed)
        self.widget_plot.plot_changed.connect(self.plot_changed)
        self.widget_plot.pipeline_changed.connect(self.pipeline_changed)
        self.widget_slot.slot_changed.connect(self.slot_changed)
        self.widget_slot.pipeline_changed.connect(self.pipeline_changed)
        self.tabWidget.setCurrentIndex(0)
        self.tabWidget.currentChanged.connect(self.update_content)

    def set_pipeline(self, pipeline):
        for widget in self.page_widgets:
            widget.set_pipeline(pipeline)
        self.update_content()

    @QtCore.pyqtSlot()
    def update_content(self):
        cur_page = self.tabWidget.currentWidget()
        for widget in self.page_widgets:
            if widget.parent() is cur_page:
                widget.update_content()
                break
