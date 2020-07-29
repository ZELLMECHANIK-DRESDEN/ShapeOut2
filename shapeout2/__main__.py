def main(splash=True):
    import os
    import pkg_resources
    import sys
    import time

    print("-2")
    from PyQt5.QtWidgets import QApplication
    # import before creating application
    import pyqtgraph  # noqa: F401

    print("-1")
    app = QApplication(sys.argv)
    imdir = pkg_resources.resource_filename("shapeout2", "img")

    sys.stdout.flush()
    print("0")
    if False:#splash:
        from PyQt5.QtWidgets import QSplashScreen
        from PyQt5.QtGui import QPixmap
        splash_path = os.path.join(imdir, "splash.png")
        splash_pix = QPixmap(splash_path)
        splash = QSplashScreen(splash_pix)
        splash.setMask(splash_pix.mask())
        splash.show()
        # make sure Qt really displays the splash screen
        time.sleep(.07)
        app.processEvents()

    print("1")
    sys.stdout.flush()
    from PyQt5 import QtCore, QtGui
    print("2")
    sys.stdout.flush()
    from .gui import ShapeOut2
    print("3")
    sys.stdout.flush()
    # Set Application Icon
    icon_path = os.path.join(imdir, "icon.png")
    app.setWindowIcon(QtGui.QIcon(icon_path))
    print("4")
    sys.stdout.flush()

    # Use dots as decimal separators
    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.C))

    print("5")
    sys.stdout.flush()

    window = ShapeOut2()
    print("6")
    sys.stdout.flush()
    window.show()
    window.raise_()

    if splash:
        splash.finish(window)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
