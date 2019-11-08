from PyQt5 import QtCore
import pyqtgraph as pg


class SimplePlotWidget(pg.PlotWidget):
    """Custom class for data visualization in Shape-Out

    Modifications include:
    - right click menu only with "Export..."
    - white background
    - top and right axes
    """
    def __init__(self, *args, **kwargs):
        super(SimplePlotWidget, self).__init__(viewBox=SimpleViewBox(),
                                               *args, **kwargs)
        # white background
        self.setBackground('w')
        # show top and right axes, but not ticklabels
        for kax in ["top", "right"]:
            self.plotItem.showAxis(kax)
            ax = self.plotItem.axes[kax]["item"]
            ax.setTicks([])
        # show grid
        self.plotItem.showGrid(x=True, y=True, alpha=.1)
        # visualization
        self.plotItem.hideButtons()


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
