import importlib.resources

from pygments import highlight, lexers, formatters
from PyQt6 import uic, QtCore, QtWidgets


class LogPanel(QtWidgets.QWidget):
    """Log panel widget

    Visualizes logs stored in the .rtdc file
    """

    def __init__(self, *args, **kwargs):
        super(LogPanel, self).__init__(*args, **kwargs)
        ref = importlib.resources.files(
            "shapeout2.gui.analysis") / "ana_log.ui"
        with importlib.resources.as_file(ref) as path_ui:
            uic.loadUi(path_ui, self)
        # current Shape-Out 2 pipeline
        self._pipeline = None
        self.listWidget_dataset.currentRowChanged.connect(
            self.on_select_dataset)
        self.listWidget_log_name.currentRowChanged.connect(
            self.on_select_log)
        self.update_content()

    @property
    def pipeline(self):
        return self._pipeline

    @QtCore.pyqtSlot(int)
    def on_select_dataset(self, ds_idx):
        """Show the logs of the dataset in the right-hand list widget"""
        self.listWidget_log_name.clear()
        if ds_idx >= 0:
            ds = self._pipeline.slots[ds_idx].get_dataset()
            for log in ds.logs:
                self.listWidget_log_name.addItem(log)

    @QtCore.pyqtSlot(int)
    def on_select_log(self, log_index):
        """Show the logs of the dataset in the right-hand list widget"""
        ds_idx = self.listWidget_dataset.currentRow()
        if ds_idx >= 0:
            ds = self._pipeline.slots[ds_idx].get_dataset()
            lines = ds.logs[list(ds.logs.keys())[log_index]]

            if lines[0].strip() == "{" and lines[-1].strip() == "}":
                # JSON
                text = highlight("\n".join(lines),
                                 lexers.JsonLexer(),
                                 formatters.HtmlFormatter(full=True,
                                                          noclasses=True,
                                                          nobackground=True))
            else:
                # Normal log
                linetypes = ["n"] * len(lines)
                for ii, line in enumerate(lines):
                    if line.count("ERROR"):
                        linetypes[ii] = "e"
                        # consecutive lines are also errors
                        for jj in range(ii+1, len(lines)):
                            if lines[jj].startswith("..."):
                                linetypes[jj] = "e"
                            else:
                                break
                    elif line.count("WARNING"):
                        linetypes[ii] = "w"
                        # consecutive lines are also errors
                        for jj in range(ii+1, len(lines)):
                            if lines[jj].startswith("..."):
                                linetypes[jj] = "w"
                            else:
                                break

                for ii, lt in enumerate(linetypes):
                    if lt == "e":
                        lines[ii] = \
                            f"<div style='color:#A60000'>{lines[ii]}</div>"
                    elif lt == "w":
                        lines[ii] = \
                            f"<div style='color:#7C4B00'>{lines[ii]}</div>"
                    else:
                        lines[ii] = f"<div>{lines[ii]}</div>"

                text = "\n".join(lines)

            self.textEdit.setText(text)
        else:
            self.listWidget_log_name.clear()
            self.textEdit.clear()

    def set_pipeline(self, pipeline):
        self._pipeline = pipeline

    def update_content(self, event=None, filt_index=None):
        if self._pipeline and self._pipeline.slots:
            self.setEnabled(True)
            self.setUpdatesEnabled(False)
            self.listWidget_dataset.clear()
            self.listWidget_log_name.clear()
            for slot in self._pipeline.slots:
                self.listWidget_dataset.addItem(slot.name)
            self.setUpdatesEnabled(True)
            self.listWidget_dataset.setCurrentRow(0)
        else:
            self.setEnabled(False)
            self.listWidget_dataset.clear()
            self.listWidget_log_name.clear()
            self.textEdit.clear()
