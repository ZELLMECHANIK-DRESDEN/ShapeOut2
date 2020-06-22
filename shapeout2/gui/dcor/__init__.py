import pkg_resources
import requests
import urllib.parse

import dclab
from PyQt5 import uic, QtCore, QtWidgets

from ... import settings
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
        self.settings = settings.SettingsFile()

        # hide SSL checkbox
        if not self.settings.get_bool("developer mode"):
            self.checkBox_ssl.hide()
        self._init_combobox()
        self.lineEdit_api_key.setText(self.settings.get_string("dcor api key"))

        # tool button
        self.pushButton_search.clicked.connect(self.on_search)
        self.pushButton_search.setDefault(True)
        self.buttonBox.buttons()[1].setDefault(False)
        self.buttonBox.buttons()[0].setDefault(False)
        self.lineEdit_search.setFocus()

    def _init_combobox(self):
        # update server list
        servs = self.settings.get_string_list("dcor servers")
        self.comboBox_server.clear()
        self.comboBox_server.addItems(servs)
        self.comboBox_server.setCurrentIndex(0)

    @show_wait_cursor
    @QtCore.pyqtSlot(int)
    def done(self, r):
        if r:
            for ii in range(self.listWidget.count()):
                item = self.listWidget.item(ii)
                if item.isSelected():
                    self.main_ui.add_dataslot(
                        paths=[self.search_results[ii][0]], is_dcor=True)
        super(DCORLoader, self).done(r)

    @show_wait_cursor
    @QtCore.pyqtSlot()
    def on_search(self):
        # update server list
        servs = self.settings.get_string_list("dcor servers")
        serv = self.comboBox_server.currentText()
        if serv.count("://"):
            serv = serv.split("://")[1]
        if serv in servs:
            # make this server the first choice
            servs.remove(serv)
        servs = [serv] + servs
        api_key = self.lineEdit_api_key.text().strip()
        # Add this API Key to the known API Keys (dclab)
        dclab.rtdc_dataset.fmt_dcor.APIHandler.add_api_key(api_key)

        # save config
        self.settings.set_string("dcor api key", api_key)
        self.settings.set_string_list("dcor servers", servs)
        self._init_combobox()

        # ready API
        http = "https" if self.checkBox_ssl.isChecked() else "http"
        base = "{}://{}/api/3".format(http, serv)
        api_headers = {"Authorization": api_key}

        # check API availability
        req = requests.get(base, headers=api_headers)
        if not req.ok:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setText("Failed to connect to DCOR server '{}'! ".format(serv)
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

    def perform_search(self, string, search_type, api_base, api_headers):
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
