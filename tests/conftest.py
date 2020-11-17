from PyQt5 import QtCore


def pytest_configure(config):
    """This is ran before all tests"""
    # disable update checking
    QtCore.QCoreApplication.setOrganizationName("Zellmechanik-Dresden")
    QtCore.QCoreApplication.setOrganizationDomain("zellmechanik.com")
    QtCore.QCoreApplication.setApplicationName("Shape-Out 2")
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    settings = QtCore.QSettings()
    settings.setIniCodec("utf-8")
    settings.setValue("check update", 0)
    settings.setValue("check pgversion", 0)
    settings.sync()
