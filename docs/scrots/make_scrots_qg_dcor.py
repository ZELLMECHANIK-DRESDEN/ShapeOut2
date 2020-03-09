"""Screenshots for quick guide dcor"""
import sys

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from shapeout2.gui.main import ShapeOut2
from shapeout2.gui import dcor

app = QApplication(sys.argv)

QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.C))

mw = ShapeOut2()
mw.settings.set_bool("developer mode", False)

# show the dialog
dlg = dcor.DCORLoader(mw)
dlg.lineEdit_api_key.setText("")
dlg.lineEdit_search.setText("reference data")
dlg.on_search()
dlg.repaint()
QApplication.processEvents()
QApplication.processEvents()
dlg.grab().save("_qg_dcor_dlg.png")
