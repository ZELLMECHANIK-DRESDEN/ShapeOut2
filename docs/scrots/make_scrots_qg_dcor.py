"""Screenshots for quick guide dcor"""
import sys

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from shapeout2.gui.main import ShapeOut2
from shapeout2.gui import dcor

app = QApplication(sys.argv)

QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.C))

mw = ShapeOut2()
mw.settings.setValue("general/check for updates", 0)
mw.settings.setValue("advanced/check pyqtgraph version", 0)

# show the dialog
dlg = dcor.DCORLoader(mw)
dlg.lineEdit_search.setText("sorting")
dlg.on_search()
# force redraw of scrollbars
dlg.listWidget.scrollToBottom()
dlg.listWidget.scrollToTop()
QApplication.processEvents()
QApplication.processEvents()
dlg.grab().save("_qg_dcor_dlg.png")
