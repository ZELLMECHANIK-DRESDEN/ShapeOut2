import pathlib
import pkg_resources
import time

from PyQt5 import uic, QtCore, QtWidgets

import dclab

from ..._version import version


class ExportData(QtWidgets.QDialog):
    def __init__(self, parent, pipeline, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent, *args, **kwargs)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.export", "e2data.ui")
        uic.loadUi(path_ui, self)
        # Get output path
        self.on_browse()
        # set pipeline
        self.pipeline = pipeline
        # update list widget
        self.on_radio()
        # Signals
        self.pushButton_path.clicked.connect(self.on_browse)
        self.toolButton_all.clicked.connect(self.on_select_all)
        self.toolButton_none.clicked.connect(self.on_select_none)
        self.radioButton_fcs.clicked.connect(self.on_radio)
        self.radioButton_rtdc.clicked.connect(self.on_radio)
        self.radioButton_tsv.clicked.connect(self.on_radio)

    @property
    def file_format(self):
        if self.radioButton_fcs.isChecked():
            return "fcs"
        elif self.radioButton_rtdc.isChecked():
            return "rtdc"
        else:
            return "tsv"

    def done(self, r):
        if r:
            self.export_data()
        super(ExportData, self).done(r)

    def export_data(self):
        """Export data to the desired file format"""
        out = pathlib.Path(self.path)
        # get features
        features = []
        for ii in range(self.listWidget.count()):
            if self.listWidget.item(ii).checkState() == 2:
                features.append(self.features[ii])
        pend = len(self.pipeline.slots)
        prog = QtWidgets.QProgressDialog("Exporting...", "Abort", 1,
                                         pend, self)
        prog.setWindowTitle("Data Export")
        prog.setWindowModality(QtCore.Qt.WindowModal)
        prog.setMinimumDuration(0)
        time.sleep(0.01)
        prog.setValue(0)
        QtWidgets.QApplication.processEvents()
        for slot_index in range(len(self.pipeline.slots)):
            ds = self.pipeline.get_dataset(slot_index)
            name = ds.path.with_suffix("." + self.file_format).name
            path = out / "SO2-export_{}_{}".format(slot_index, name)
            if self.file_format == "rtdc":
                ds.export.hdf5(path=path,
                               features=features,
                               override=True)
            elif self.file_format == "fcs":
                ds.export.fcs(path=path,
                              features=features,
                              meta_data={"Shape-Out version": version},
                              override=True)
            else:
                ds.export.tsv(path=path,
                              features=features,
                              meta_data={"Shape-Out version": version},
                              override=True)
            if prog.wasCanceled():
                break
            prog.setValue(slot_index + 1)
            QtWidgets.QApplication.processEvents()
        prog.setValue(pend)

    def on_browse(self):
        out = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                         'Export directory')
        if out:
            self.path = out
            self.lineEdit_path.setText(self.path)
        else:
            self.path = None

    def on_radio(self):
        scalar = self.file_format != "rtdc"
        self.update_feature_list(scalar)

    def on_select_all(self):
        for ii in range(self.listWidget.count()):
            wid = self.listWidget.item(ii)
            wid.setCheckState(2)

    def on_select_none(self):
        for ii in range(self.listWidget.count()):
            wid = self.listWidget.item(ii)
            wid.setCheckState(0)

    def update_feature_list(self, scalar=False):
        self.features = self.pipeline.get_features(scalar=scalar, union=True,
                                                   label_sort=True)

        self.listWidget.clear()
        for feat in self.features:
            wid = QtWidgets.QListWidgetItem(dclab.dfn.feature_name2label[feat])
            wid.setCheckState(2)
            self.listWidget.addItem(wid)
