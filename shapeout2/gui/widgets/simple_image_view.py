import pyqtgraph as pg

from .simple_plot_widget import SimpleViewBox


class SimpleImageView(pg.ImageView):
    """Custom class for data visualization in Shape-Out"""

    def __init__(self, *args, **kwargs):
        super(SimpleImageView, self).__init__(view=SimpleImageViewBox(),
                                              *args, **kwargs)
        # disable pyqtgraph controls we don't need
        self.ui.histogram.hide()
        self.ui.roiBtn.hide()
        self.ui.menuBtn.hide()
        # disable keyboard shortcuts
        self.keyPressEvent = lambda _: None
        self.keyReleaseEvent = lambda _: None


class SimpleImageViewBox(SimpleViewBox):
    def raiseContextMenu(self, ev):
        # nothing
        return True
