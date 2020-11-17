import pkg_resources
import requests
import urllib.parse
import webbrowser

import dclab
from PyQt5 import uic, QtCore, QtGui, QtWidgets

from ..widgets import show_wait_cursor


class DCORLoader(QtWidgets.QDialog):
    def __init__(self, parent, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, parent, *args, **kwargs)
        path_ui = pkg_resources.resource_filename(
            "shapeout2.gui.dcor", "dcor.ui")
        uic.loadUi(path_ui, self)

        self.main_ui = parent
        self.search_results = []

        # Update UI
        self.settings = QtCore.QSettings()

        # tool button
        self.pushButton_search.clicked.connect(self.on_search)
        self.pushButton_search.setDefault(True)
        self.buttonBox.buttons()[1].setDefault(False)
        self.buttonBox.buttons()[0].setDefault(False)
        self.lineEdit_search.setFocus()

        # signals
        btn_close = self.buttonBox.button(QtGui.QDialogButtonBox.Close)
        btn_close.clicked.connect(self.on_close)
        btn_close.setToolTip("Close this window.")
        btn_open = self.buttonBox.button(QtGui.QDialogButtonBox.Apply)
        btn_open.clicked.connect(self.on_open)
        btn_open.setToolTip("Add selected resources to current session.")
        btn_open.setText("Add to session")
        plusicon = QtGui.QIcon.fromTheme("list-add")
        btn_open.setIcon(plusicon)
        btn_help = self.buttonBox.button(QtGui.QDialogButtonBox.Help)
        btn_help.clicked.connect(self.on_help)
        btn_help.setToolTip("View DCOR Quick Guide online.")

    @staticmethod
    def perform_search(string, search_type, api_base, api_headers):
        """Perform search

        Parameters
        ----------
        string: str
            Search string (already parsed using urllib.parse.quote)
        search_type: str
            "free": free text search
            or "dataset": resource/package name/id
        api_base: str
            Everything up until "https://server.example.org/api/3"
        api_headers: dict
            Headers for the request
        """
        if search_type == "free":
            url = api_base + "/action/package_search?q={}".format(string)
            # limit to 20 rows
            url += "&rows=20"
            # include private data
            url += "&include_private=True"
            urls = [url]
        else:
            urls = [
                api_base + "/action/package_show?id={}".format(string),
                api_base + "/action/resource_show?id={}".format(string),
            ]

        pkg_res = []
        for url in urls:
            req = requests.get(url, headers=api_headers)
            if not req.ok:
                continue
            resp = req.json()["result"]
            if "count" in resp and "results" in resp:
                # free search
                for pkg in resp["results"]:
                    if "resources" in pkg:
                        for res in pkg["resources"]:
                            pkg_res.append([pkg, res])
            elif "resources" in resp:
                # package show
                for res in resp["resources"]:
                    pkg_res.append([resp, res])
            else:
                # resource show
                purl = api_base + "/action/package_show?id={}".format(
                    resp["package_id"])
                pkg = requests.get(purl, headers=api_headers).json()["result"]
                pkg_res.append([pkg, resp])

        res_list = []
        failed = []
        for pkg, res in pkg_res:
            # check availability of each resource
            c = api_base + "/action/dcserv?id={}&query=valid".format(res["id"])
            req = requests.get(c, headers=api_headers)
            if req.ok:
                if req.json()["result"]:  # only use valid data
                    name = "{}: {} <{}@{}>".format(
                        pkg["title"],
                        res["name"],
                        pkg["name"],
                        pkg["organization"]["name"],
                    )
                    ru = api_base + "/action/dcserv?id={}".format(res["id"])
                    res_list.append([ru, name])
            else:
                failed.append("{}: {}".format(res["id"], req.reason))
        if failed:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setText("Search found invalid data: {}".format(failed))
            msg.setWindowTitle("Dataset validation")
            msg.exec_()
        return res_list

    @QtCore.pyqtSlot()
    def on_close(self):
        """close window"""
        self.close()

    @show_wait_cursor
    @QtCore.pyqtSlot()
    def on_open(self):
        """Add selected resources to the current session"""
        for ii in range(self.listWidget.count()):
            item = self.listWidget.item(ii)
            if item.isSelected():
                self.main_ui.add_dataslot(
                    paths=[self.search_results[ii][0]], is_dcor=True)

    @QtCore.pyqtSlot()
    def on_help(self):
        """Show Shape-Out 2 docs"""
        webbrowser.open(
            "https://shapeout2.readthedocs.io/en/stable/sec_qg_dcor.html")

    @show_wait_cursor
    @QtCore.pyqtSlot()
    def on_search(self):
        server = self.settings.value("dcor/servers", ["dcor.mpl.mpg.de"])[0]
        api_key = self.settings.value("dcor/api key", "")
        use_ssl = bool(int(self.settings.value("dcor/use ssl", 1)))
        # Add this API Key to the known API Keys (dclab)
        dclab.rtdc_dataset.fmt_dcor.APIHandler.add_api_key(api_key)

        # ready API
        http = "https" if use_ssl else "http"
        base = "{}://{}/api/3".format(http, server)
        if api_key:
            api_headers = {"Authorization": api_key}
        else:
            api_headers = {}

        # check API availability
        req = requests.get(base, headers=api_headers)
        if not req.ok:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setText("Failed to connect to server '{}'! ".format(server)
                        + "Reason: {}".format(req.reason))
            msg.setWindowTitle("Connection failed")
            msg.exec_()
            return
        if "version" not in req.json() or req.json()["version"] != 3:
            raise ValueError("Invalid response: {}".format(req.json()))

        # perform search
        if self.comboBox_search.currentIndex() == 1:
            stype = "dataset"
        else:
            stype = "free"
        search_string = urllib.parse.quote(self.lineEdit_search.text())
        res = self.perform_search(search_string, stype, base, api_headers)
        self.listWidget.clear()
        for r in res:
            self.listWidget.addItem(r[1])
        self.search_results = res
