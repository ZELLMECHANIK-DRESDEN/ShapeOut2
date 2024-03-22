import pathlib
import pkg_resources

from PyQt5 import uic, QtCore, QtWidgets

import dclab

from ..widgets import show_wait_cursor

from ...util import get_valid_filename
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
        self.bulklist_features.set_title("Features")
        self.on_radio()
        self.on_select_features_innate()
        # Signals
        self.pushButton_path.clicked.connect(self.on_browse)
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

    @show_wait_cursor
    @QtCore.pyqtSlot()
    def export_data(self):
        """Export data to the desired file format"""
        # get features
        features = self.bulklist_features.get_selection()
        pend = len(self.pipeline.slots)
        prog = QtWidgets.QProgressDialog("Exporting...", "Abort", 1,
                                         pend, self)
        prog.setWindowTitle("Data Export")
        prog.setWindowModality(QtCore.Qt.WindowModal)
        prog.setMinimumDuration(0)
        prog.setValue(0)
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, 300)

        slots_n_paths = self.get_export_filenames()
        prog.setMaximum(len(slots_n_paths))  # correct dialog maximum

        for slot_index, path in slots_n_paths:
            ds = self.pipeline.get_dataset(slot_index)
            # check features
            fmiss = [ff for ff in features if ff not in ds.features]
            if fmiss:
                lmiss = [dclab.dfn.get_feature_label(ff) for ff in fmiss]
                QtWidgets.QMessageBox.warning(
                    self,
                    "Features missing!",
                    (f"Dataslot {slot_index} does not have these features:"
                     + "\n"
                     + "".join([f"\n- {fl}" for fl in lmiss])
                     + "\n\n"
                     + f"They are not exported to .{self.file_format}!")
                )
            if self.file_format == "rtdc":
                ds.export.hdf5(
                    path=path,
                    features=[ff for ff in features if ff in ds.features],
                    logs=True,
                    tables=True,
                    meta_prefix="",
                    override=False)
            elif self.file_format == "fcs":
                ds.export.fcs(
                    path=path,
                    features=[ff for ff in features if ff in ds.features],
                    meta_data={"Shape-Out version": version},
                    override=False)
            else:
                ds.export.tsv(
                    path=path,
                    features=[ff for ff in features if ff in ds.features],
                    meta_data={"Shape-Out version": version},
                    override=False)
            if prog.wasCanceled():
                break
            prog.setValue(slot_index + 1)
            QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents,
                                                 300)
        prog.setValue(pend)

    def get_export_filenames(self):
        """Compute names for exporting data, avoiding overriding anything

        Return a list of tuples `(slot_index, filename)`.
        """
        # for every slot there is a path
        slots_n_paths = []
        out = pathlib.Path(self.path)
        # assemble the slots
        slots = []
        for s_index in range(len(self.pipeline.slots)):
            slot = self.pipeline.slots[s_index]
            if slot.slot_used:
                slots.append((s_index, slot))
        # find non-existent file names
        ap = ""  # this gets appended to the file stem if the file exists
        counter = 0  # counts up an index for appending to the file
        while True:
            slots_n_paths.clear()
            for s_index, slot in slots:
                fn = f"SO2-export_{s_index}_{slot.name}{ap}.{self.file_format}"
                # remove bad characters from file name
                fn = get_valid_filename(fn)
                path = out / fn
                if path.exists():
                    # The file already exists. Break here and the counter
                    # is incremented for a next iteration.
                    break
                else:
                    # Everything good so far.
                    slots_n_paths.append((s_index, path))
            else:
                # If nothing in the for loop caused it to break, then we
                # have a fully populated list of slots_n_paths, and we can
                # exit this while-loop.
                break

            counter += 1
            ap = f"_{counter}"
        # Return the list of slots and corresponding paths
        return slots_n_paths

    def on_browse(self):
        out = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                         'Export directory')
        if out:
            self.path = out
            self.lineEdit_path.setText(self.path)
        else:
            self.path = None

    def on_radio(self):
        self.update_feature_list()

    def on_select_features_innate(self):
        """Only select all innate features of the first dataset"""
        if self.pipeline.num_slots:
            ds = self.pipeline.get_dataset(0)
            features_innate = ds.features_innate
            lw = self.bulklist_features.listWidget
            for ii in range(lw.count()):
                wid = lw.item(ii)
                for feat in features_innate:
                    if wid.data(101) == feat:
                        wid.setCheckState(QtCore.Qt.CheckState.Checked)
                        break
                else:
                    wid.setCheckState(QtCore.Qt.CheckState.Unchecked)

    def update_feature_list(self, scalar=False):
        if self.file_format == "rtdc":
            self.features = self.pipeline.get_features(union=True,
                                                       label_sort=True)
            # do not allow exporting event index, since it will be
            # re-enumerated in any case.
            self.features.remove("index")
        else:
            self.features = self.pipeline.get_features(scalar=True,
                                                       union=True,
                                                       label_sort=True)
        labels = [dclab.dfn.get_feature_label(feat) for feat in self.features]
        self.bulklist_features.set_items(self.features, labels)
