import importlib.resources
import io

import numpy as np
import pyqtgraph as pg
from PyQt6 import uic, QtCore, QtGui, QtWidgets

#: Fallback graph colors
FALLBACK_COLORS = {
    'brightness': '#d8d000',
    'cpu_cs': '#b41010',
    'cpu_sys': '#8e0505',
    'disk': '#949494',
    'flow_rate_sample': '#00049C',
    'flow_rate_sheath': '#00049C',
    'focus': '#a03000',
    'imaging_rate': '#6b02e8',
    'pressure_sample': '#7c7c7c',
    'pressure_sheath': '#6c6c6c',
    'ram_cam': '#db8400',
    'ram_wrt': '#bf770a',
    'recording_rate': '#4858e8',
    'rotation': '#6ecf0d',
    'shift': '#0e8f69',
    'temperature_camera': '#8005b8',
    'temperature_chip': '#b80589',
    'time': '#000000'
}


def get_foreground_for_background(color):
    """Given background color, yield black or white"""
    color = QtGui.QColor(color)
    color_mean = np.mean([color.red(), color.blue(), color.green()])
    if color_mean < 255 / 2:
        return "white"
    else:
        return "black"


class TablesPanel(QtWidgets.QWidget):
    """Tables panel widget

    Visualizes tables stored in the .rtdc file
    """

    def __init__(self, *args, **kwargs):
        super(TablesPanel, self).__init__(*args, **kwargs)
        ref = importlib.resources.files(
            "shapeout2.gui.analysis") / "ana_tables.ui"
        with importlib.resources.as_file(ref) as path_ui:
            uic.loadUi(path_ui, self)
        # current Shape-Out 2 pipeline
        self._pipeline = None
        self._selected_table = None
        self._selected_graphs = []
        self.legend = pg.LegendItem((80, 60),
                                    offset=(40, 20))
        self.legend.setParentItem(self.graphicsView.graphicsItem())
        self.graphicsView.showGrid(True, True)
        self.tabWidget.setCurrentIndex(0)

        self.listWidget_dataset.currentRowChanged.connect(
            self.on_select_dataset)
        self.listWidget_table_name.currentRowChanged.connect(
            self.on_select_table)
        self.listWidget_table_graphs.itemSelectionChanged.connect(
            self.on_select_graphs)
        self.update_content()

    @property
    def pipeline(self):
        return self._pipeline

    @QtCore.pyqtSlot(int)
    def on_select_dataset(self, ds_idx):
        """Show the tables of the dataset in the right-hand list widget"""
        self.listWidget_table_name.clear()
        self.listWidget_table_graphs.clear()
        if ds_idx >= 0:
            ds = self._pipeline.slots[ds_idx].get_dataset()
            table_names = list(ds.tables.keys())
            self.listWidget_table_name.blockSignals(True)
            for table in table_names:
                self.listWidget_table_name.addItem(table)
            self.listWidget_table_name.blockSignals(False)

            # Apply previously selected tables
            if self._selected_table in table_names:
                table_idx = table_names.index(self._selected_table)
                self.listWidget_table_name.setCurrentRow(table_idx)

    @QtCore.pyqtSlot(int)
    def on_select_table(self, table_index):
        """Show the tables of the dataset in the right-hand list widget"""
        ds_idx = self.listWidget_dataset.currentRow()
        if ds_idx >= 0 and table_index >= 0:
            ds = self._pipeline.slots[ds_idx].get_dataset()
            self._selected_table = list(ds.tables.keys())[table_index]
            table = ds.tables[self._selected_table]
            names = table[:].dtype.names

            self.listWidget_table_graphs.blockSignals(True)
            self.listWidget_table_graphs.clear()

            for ii, graph in enumerate(names):
                self.listWidget_table_graphs.addItem(graph)
                color = table.attrs.get(f"COLOR_{graph}",
                                        FALLBACK_COLORS.get(graph,
                                                            "black")
                                        )
                self.listWidget_table_graphs.item(ii).setBackground(
                    QtGui.QColor(color))
                self.listWidget_table_graphs.item(ii).setForeground(
                    QtGui.QColor(get_foreground_for_background(color)))

            # Apply previously selected graphs
            for graph in names:
                if graph in list(self._selected_graphs):
                    graph_index = names.index(graph)
                    item = self.listWidget_table_graphs.item(graph_index)
                    if item:
                        item.setSelected(True)
            self.listWidget_table_graphs.blockSignals(False)
            self.on_select_graphs()
        else:
            self.listWidget_table_name.clear()
            self.listWidget_table_graphs.clear()

    @QtCore.pyqtSlot()
    def on_select_graphs(self):
        """Show the graphs of one table of a dataset"""
        ds_idx = self.listWidget_dataset.currentRow()
        table_index = self.listWidget_table_name.currentRow()
        if ds_idx >= 0 and table_index >= 0:
            items = self.listWidget_table_graphs.selectedIndexes()
            self._selected_graphs = [it.data() for it in items]
            ds = self._pipeline.slots[ds_idx].get_dataset()
            table = ds.tables[list(ds.tables.keys())[table_index]]
            table_data = table[:]
            # assemble the graph list
            graph_list = []
            if "time" in table_data.dtype.names:
                x_vals = {"name": "time",
                          "data": table_data["time"].flatten()}
            else:
                x_vals = {"name": "index",
                          "data": np.arange(len(table_data))}

            for graph in self._selected_graphs:
                graph_list.append({
                    "name": graph,
                    "data": table_data[graph].flatten(),
                    "color": table.attrs.get(f"COLOR_{graph}",
                                             FALLBACK_COLORS.get(graph,
                                                                 "black")
                                             )
                })
            # show the graph
            self.show_graph(x_vals, graph_list)
            self.show_raw_data(graph_list)
            self.graphicsView.autoRange()
        else:
            self.listWidget_table_graphs.clear()

    def set_pipeline(self, pipeline):
        self._pipeline = pipeline

    def show_graph(self, x_vals, graph_list):
        self.graphicsView.clear()
        self.legend.clear()
        for item in graph_list:
            pl = self.graphicsView.plot(
                pen={"color": item["color"],
                     "width": 2},
                x=x_vals["data"],
                y=item["data"],
                name=item["name"],
            )

            self.legend.addItem(pl, item["name"])
        self.graphicsView.plotItem.setLabels(bottom=x_vals["name"])

    def show_raw_data(self, graph_list):
        text = "\t".join(it["name"] for it in graph_list)
        # save the array into a temporary string
        s = io.StringIO()
        data = np.array([it["data"] for it in graph_list]).transpose()
        np.savetxt(s, data, delimiter="\t", fmt="%.5g", header=text)
        self.plainTextEdit_raw.setPlainText(s.getvalue())

    def update_content(self, event=None, filt_index=None):
        if self._pipeline and self._pipeline.slots:
            self.setEnabled(True)
            self.setUpdatesEnabled(False)
            self.listWidget_dataset.clear()
            self.listWidget_table_name.clear()
            for slot in self._pipeline.slots:
                self.listWidget_dataset.addItem(slot.name)
            self.setUpdatesEnabled(True)
            self.listWidget_dataset.setCurrentRow(0)
        else:
            self.setEnabled(False)
            self.listWidget_dataset.clear()
            self.listWidget_table_name.clear()
