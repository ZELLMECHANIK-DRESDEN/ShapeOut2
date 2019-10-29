import pkg_resources

from PyQt5 import uic, QtWidgets


class AnalysisView(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.analysis", "ana_view.ui")
        uic.loadUi(path_ui, self)
        self.setWindowTitle("Analysis View")
        self.setMinimumSize(self.sizeHint())

    def update_content(self):
        self.widget_filter.update_content()
        self.widget_meta.update_content()
        self.widget_plot.update_content()
        self.widget_slot.update_content()
