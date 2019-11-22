import pathlib
import pkg_resources

from PyQt5 import uic, QtWidgets

import dclab

from ... import session


class ExportFilter(QtWidgets.QDialog):
    def __init__(self, parent, pipeline, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent, *args, **kwargs)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.export", "e2filter.ui")
        uic.loadUi(path_ui, self)
        # set pipeline
        self.pipeline = pipeline

    @property
    def file_format(self):
        if self.radioButton_poly.isChecked():
            return "poly"
        else:
            return "sof"

    @property
    def file_mode(self):
        if self.radioButton_single.isChecked():
            return "single"
        else:
            return "multiple"

    def done(self, r):
        if r:
            self.export_filters()
        super(ExportFilter, self).done(r)

    def export_filters(self):
        """Export filters"""
        if self.file_mode == "single":
            # all in one file
            if self.file_format == "poly":
                cap = "Polygon filter files (*.poly)"
                path, _ = QtWidgets.QFileDialog.getSaveFileName(
                    self, 'Save polygon filters', '', cap)
                if not path.endswith(".poly"):
                    path += ".poly"
                dclab.PolygonFilter.save_all(path)
            else:
                cap = "Shape-Out 2 filter files (*.sof)"
                path, _ = QtWidgets.QFileDialog.getSaveFileName(
                    self, 'Save polygon filters', '', cap)
                if not path.endswith(".sof"):
                    path += ".sof"
                session.export_filters(path=path,
                                       pipeline=self.pipeline)
        else:
            # one file per filter
            path = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                              'Output Folder')
            if self.file_format == "poly":
                for pf in dclab.PolygonFilter.instances:
                    name = "SO-PolygonFilter_{}.poly".format(pf.unique_id)
                    out = pathlib.Path(path) / name
                    pf.save(out)
            else:
                for filt_id in self.pipeline.filter_ids:
                    name = "SO-Filter_{}.sof".format(filt_id)
                    out = pathlib.Path(path) / name
                    session.export_filters(path=out,
                                           pipeline=self.pipeline,
                                           filt_ids=[filt_id])
