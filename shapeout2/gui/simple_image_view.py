from PyQt5 import QtCore
import pyqtgraph as pg


class SimpleImageView(pg.ImageView):
    """Custom class for data visualization in Shape-Out

    Modifications include:
    - right click menu only with "Export..."
    - white background
    - top and right axes
    """

    def __init__(self, *args, **kwargs):
        super(SimpleImageView, self).__init__(view=SimpleViewBox(),
                                              *args, **kwargs)
        # disable pyqtgraph controls we don't need
        self.ui.histogram.hide()
        self.ui.roiBtn.hide()
        self.ui.menuBtn.hide()
        # disable keyboard shortcuts
        self.keyPressEvent = lambda _: None
        self.keyReleaseEvent = lambda _: None


class SimpleViewBox(pg.ViewBox):
    set_scatter_point = QtCore.pyqtSignal(QtCore.QPointF)
    add_poly_vertex = QtCore.pyqtSignal(QtCore.QPointF)

    #: allowed right-click menu
    right_click_actions = ["Export..."]

    def raiseContextMenu(self, ev):
        # Let the scene add on to the end of our context menu
        # (this is optional)
        menu = self.scene().addParentContextMenus(self, self.menu, ev)

        # Only keep list of action defined in `self.right_click_actions`
        for action in self.menu.actions():
            if action.text() not in self.right_click_actions:
                self.menu.removeAction(action)

        pos = ev.screenPos()
        menu.popup(QtCore.QPoint(pos.x(), pos.y()))
        return True
