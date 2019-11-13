from PyQt5 import QtCore
import pyqtgraph as pg


class SimplePlotItem(pg.PlotItem):
    """Custom class for data visualization in Shape-Out

    Modifications include:
    - right click menu only with "Export..."
    - top and right axes
    """

    def __init__(self, *args, **kwargs):
        if "viewBox" not in kwargs:
            kwargs["viewBox"] = SimpleViewBox()
        super(SimplePlotItem, self).__init__(*args, **kwargs)
        # show top and right axes, but not ticklabels
        for kax in ["top", "right"]:
            self.showAxis(kax)
            ax = self.axes[kax]["item"]
            ax.setTicks([])
            ax.setLabel(None)
            ax.setStyle(tickTextOffset=0,
                        tickTextWidth=0,
                        tickTextHeight=0,
                        autoExpandTextSpace=False,
                        showValues=False,
                        )
        # show grid
        self.showGrid(x=True, y=True, alpha=.1)
        # visualization
        self.hideButtons()


class SimplePlotWidget(pg.PlotWidget):
    """Custom class for data visualization in Shape-Out

    Modifications include:
    - white background
    - those of SimplePlotItem
    """

    def __init__(self, parent=None, background='w', **kargs):
        # The following code is copied from pg.PlotWidget and instead
        # of PlotItem we use SimplePlotItem.
        pg.GraphicsView.__init__(self, parent, background=background)
        self.enableMouse(False)
        self.plotItem = SimplePlotItem(**kargs)
        self.setCentralItem(self.plotItem)
        # Explicitly wrap methods from plotItem
        for m in [
            'addItem', 'removeItem', 'autoRange', 'clear', 'setXRange',
            'setYRange', 'setRange', 'setAspectLocked', 'setMouseEnabled',
            'setXLink', 'setYLink', 'enableAutoRange', 'disableAutoRange',
                'setLimits', 'register', 'unregister', 'viewRect']:
            setattr(self, m, getattr(self.plotItem, m))
        self.plotItem.sigRangeChanged.connect(self.viewRangeChanged)


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
