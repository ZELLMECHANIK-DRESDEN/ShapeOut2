import codecs
import numbers
import pathlib
import pkg_resources
import time

import dclab
from PyQt5 import uic, QtWidgets

from ...pipeline import Pipeline
from ..._version import version

STAT_METHODS = sorted(dclab.statistics.Statistics.available_methods.keys())
STAT_METHODS.remove("%-gated")  # This does not make sense with Pipeline


class ComputeStatistics(QtWidgets.QDialog):
    def __init__(self, parent, pipeline, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent, *args, **kwargs)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.compute", "comp_stats.ui")
        uic.loadUi(path_ui, self)
        # for external statistics
        self.path = None
        # set pipeline
        self.pipeline = pipeline
        # Signals
        self.pushButton_path.clicked.connect(self.on_browse)
        self.comboBox.currentIndexChanged.connect(self.on_combobox)
        # Populate statistics methods
        self.listWidget_stats.clear()
        for meth in STAT_METHODS:
            wid = QtWidgets.QListWidgetItem(meth)
            wid.setCheckState(2)
            self.listWidget_stats.addItem(wid)
        # initialize rest
        if len(self.pipeline.slots) == 0:
            self.comboBox.setCurrentIndex(1)
        else:
            self.comboBox.setCurrentIndex(0)
        self.on_combobox()  # computes self.features

    def done(self, r):
        if r:
            success = self.export_statistics()
        else:
            success = True
        if success:
            super(ComputeStatistics, self).done(r)

    def export_statistics(self):
        """Export statistics to .tsv"""
        # get features
        features = []
        for ii in range(self.listWidget_features.count()):
            if self.listWidget_features.item(ii).checkState() == 2:
                features.append(self.features[ii])
        # get methods
        methods = []
        for ii in range(self.listWidget_stats.count()):
            if self.listWidget_stats.item(ii).checkState() == 2:
                methods.append(STAT_METHODS[ii])

        prog = QtWidgets.QProgressDialog("Computing statistics...", "Abort", 1,
                                         1, self)
        prog.setMinimumDuration(0)
        time.sleep(0.01)
        prog.setValue(0)
        # compute statistics
        values = []
        if self.comboBox.currentIndex() == 0:
            # from pipeline
            datasets = self.pipeline.get_datasets()
            prog.setMaximum(len(datasets))
            for ii, ds in enumerate(datasets):
                h, v = dclab.statistics.get_statistics(ds,
                                                       methods=methods,
                                                       features=features)
                h = ["Path", "Slot", "Name"] + h
                v = ["{}".format(ds.path), ii, ds.title] + v
                values.append(v)
                if prog.wasCanceled():
                    break
                prog.setValue(ii + 1)
                QtWidgets.QApplication.processEvents()
        else:
            # from path
            path = pathlib.Path(self.path)
            files = sorted(path.rglob("*.rtdc"))
            prog.setMaximum(len(files))
            for ii, pp in enumerate(files):
                ds = dclab.new_dataset(pp)
                h, v = dclab.statistics.get_statistics(ds,
                                                       methods=methods,
                                                       features=features)
                h = ["Path", "Name"] + h
                v = ["{}".format(ds.path), ds.title] + v
                values.append(v)
                prog.setValue(ii + 1)
                QtWidgets.QApplication.processEvents()
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save statistics', '', 'tab-separated values (*.tsv)')
        if not path:
            # Abort export
            return False
        elif not path.endswith(".tsv"):
            path += ".tsv"

        # Header
        header = ["Statistics Output",
                  "Shape-Out {}".format(version),
                  "",
                  "\t".join(h),
                  ]
        # Data
        data = []
        for v in values:
            line = []
            for vi in v:
                if (isinstance(vi, numbers.Real)
                        and not isinstance(vi, numbers.Integral)):
                    line.append("{:.5e}".format(vi))
                else:
                    line.append("{}".format(vi))
            data.append("\t".join(line))
        # Write BOM
        with path.open("wb") as fd:
            fd.write(codecs.BOM_UTF8)
        # Write rest
        with path.open("a", encoding="utf-8") as fd:
            for line in header:
                fd.write("# " + line + "\r\n")
            for line in data:
                fd.write(line + "\r\n")
        return True  # True means success

    def on_browse(self):
        out = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                         'Export directory')
        if out:
            self.path = out
            self.lineEdit_path.setText(self.path)
            self.comboBox.setCurrentIndex(1)
        else:
            self.path = None
            self.comboBox.setCurrentIndex(0)

    def on_combobox(self):
        if self.comboBox.currentIndex() == 1:
            self.widget_path.show()
            if self.path is None:
                self.on_browse()
            if self.path:
                self.update_feature_list(use_pipeline=False)
                # else, on_combobox is triggered again
        else:
            self.widget_path.hide()
            self.update_feature_list(use_pipeline=True)

    def update_feature_list(self, use_pipeline=True):
        if use_pipeline:
            self.features = self.pipeline.get_features(scalar=True,
                                                       union=True,
                                                       label_sort=True)
        else:
            # This is just a cheap way of getting a label-sorted list
            # of all scalar features.
            empty_pipeline = Pipeline()
            self.features = empty_pipeline.get_features(scalar=True,
                                                        label_sort=True)

        self.listWidget_features.clear()
        for feat in self.features:
            wid = QtWidgets.QListWidgetItem(dclab.dfn.feature_name2label[feat])
            wid.setCheckState(0)
            self.listWidget_features.addItem(wid)
