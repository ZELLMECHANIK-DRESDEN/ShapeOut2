import pathlib

from PyQt5 import QtCore, QtWidgets

from .matrix_dataset import MatrixDataset
from .matrix_filter import MatrixFilter
from .matrix_element import MatrixElement


class DataMatrix(QtWidgets.QWidget):
    quickviewed = QtCore.pyqtSignal(pathlib.Path, list)

    def __init__(self, parent=None, analysis=range(3)):
        super(DataMatrix, self).__init__(parent)

        self.layout = QtWidgets.QGridLayout()
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.setAcceptDrops(True)

    def add_dataset(self, path, row=None):
        nrows = self.layout.rowCount()
        if nrows == 1:
            self.add_filter()

        if row is None:
            self.layout.addWidget(MatrixDataset(path), nrows, 0)
        else:
            # TODO: insert dataset at row
            assert False

        self.fill_elements()
        self.adjust_size()

    def add_filter(self, evt=None):
        ncols = self.layout.columnCount()
        name = "FS{}".format(ncols)
        self.layout.addWidget(MatrixFilter(name), 0, ncols)
        self.fill_elements()
        self.adjust_size()

    def adjust_size(self):
        ncols = self.layout.columnCount()
        nrows = self.layout.rowCount()
        if ncols > 1 and nrows > 1:
            hwidth = self.layout.itemAtPosition(0, 1).geometry().width() + 2
            hheight = self.layout.itemAtPosition(0, 1).geometry().height() + 2
            dwidth = self.layout.itemAtPosition(1, 0).geometry().width() + 2
            dheight = self.layout.itemAtPosition(1, 0).geometry().height() + 2

            self.setMinimumSize((ncols-1)*hwidth+dwidth,
                                (nrows-1)*dheight+hheight)

    def clear(self):
        # TODO
        raise NotImplementedError("Clear not implemented")

    def dragEnterEvent(self, event):
        print("drag enter event on data matrix")
        event.ignore()

    def dropEvent(self, event):
        print("drag drop event on data matrix")
        event.ignore()

    def fill_elements(self):
        ncols = self.layout.columnCount()
        nrows = self.layout.rowCount()
        for ii in range(1, nrows):
            for jj in range(1, ncols):
                if self.layout.itemAtPosition(ii, jj) is None:
                    me = MatrixElement()
                    me.quickview_selected.connect(self.update_quickview)
                    self.layout.addWidget(me, ii, jj)

    def get_dataset_paths(self):
        """Return dataset paths in the order they are displayed"""
        nrows = self.layout.rowCount()
        paths = []
        for ii in range(1, nrows):
            item = self.layout.itemAtPosition(ii, 0)
            paths.append(item.widget().path)
        return paths

    def update_content(self):
        ncols = self.layout.columnCount()
        nrows = self.layout.rowCount()
        for ii in range(1, nrows):
            for jj in range(1, ncols):
                item = self.layout.itemAtPosition(ii, jj)
                if isinstance(item, MatrixElement):
                    item.update_content()

    @QtCore.pyqtSlot()
    def update_quickview(self):
        idx = self.layout.indexOf(self.sender())
        row, column, _, _ = self.layout.getItemPosition(idx)
        # decrement by header row/column
        row -= 1  # enumerates the dataset
        column -= 1  # enumerates the filter

        paths = self.get_dataset_paths()
        filters = []
        self.quickviewed.emit(paths[row], filters)
