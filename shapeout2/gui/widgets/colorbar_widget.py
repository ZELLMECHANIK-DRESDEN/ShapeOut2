import numpy as np
from PyQt5 import QtGui
import pyqtgraph as pg
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients


class ColorBarWidget(pg.GraphicsWidget):
    def __init__(self, cmap, width, height, vmin=0.0, vmax=1.0, label=""):
        """Colorbar widget that can be added to a layout

        This widget can be added to a GraphicsLayout. It is designed to
        work well with the Shape-Out plot layout.

        Parameters
        ----------
        cmap: str
            Name of the colormap
        width: int
            Width of the colorbar
        height:
            Height of the colorbar
        vmin: float
            Lower value of the colorbar
        vmax: float
            Upper value of the colorbar
        label: str
            Label placed next to the colorbar

        Notes
        -----
        Inspired by https://gist.github.com/maedoc/b61090021d2a5161c5b9
        """
        pg.GraphicsWidget.__init__(self)
        self.setSizePolicy(QtGui.QSizePolicy.Fixed,
                           QtGui.QSizePolicy.Preferred)

        # arguments
        pcmap = pg.ColorMap(*zip(*Gradients[cmap]["ticks"]))
        w = width
        h = height
        stops, colors = pcmap.getStops('float')
        smn, spp = stops.min(), stops.ptp()
        stops = (stops - stops.min())/stops.ptp()
        ticks = np.r_[0.0:1.0:5j, 1.0] * spp + smn
        tick_labels = ["%0.2g" % (t,) for t in np.linspace(vmin, vmax, 5)]

        # setup picture
        self.pic = pg.QtGui.QPicture()
        p = pg.QtGui.QPainter(self.pic)

        # draw bar with gradient following colormap
        p.setPen(pg.mkPen('k'))
        grad = pg.QtGui.QLinearGradient(w/2.0, 0.0, w/2.0, h*1.0)
        for stop, color in zip(stops, colors):
            grad.setColorAt(1.0 - stop, pg.QtGui.QColor(*[c for c in color]))
        p.setBrush(pg.QtGui.QBrush(grad))
        p.drawRect(pg.QtCore.QRectF(0, 0, w, h))

        # draw ticks & tick labels
        mintx = 0.0
        maxwidth = 0.0
        for tick, tick_label in zip(ticks, tick_labels):
            y_ = (1.0 - (tick - smn)/spp) * h
            p.drawLine(w, int(y_), int(w+5.0), int(y_))
            br = p.boundingRect(
                0, 0, 0, 0, pg.QtCore.Qt.AlignRight, tick_label)
            if br.x() < mintx:
                mintx = br.x()
            if br.width() > maxwidth:
                maxwidth = br.width()
            p.drawText(int(br.x() + 10.0 + w + br.width()),
                       int(y_ + br.height() / 4.0),
                       tick_label)

        # draw label
        br = p.boundingRect(0, 0, 0, 0, pg.QtCore.Qt.AlignBottom, label)
        p.rotate(90)
        p.drawText(int(h/2 - br.width()/2),
                   int(-w-maxwidth-15),
                   label)

        # done
        p.end()

        # set minimum sizes (how do you get the actual bounding rect?)
        br = self.pic.boundingRect()
        self.setMinimumWidth(br.width() + maxwidth + 20)
        self.setMinimumHeight(h)

        # alognment with other Shape-Out plots (kind of a workaround)
        self.translate(0, 40)

    def paint(self, p, *args):
        # paint underlying mask
        p.setPen(pg.QtGui.QColor(255, 255, 255, 0))
        p.setBrush(pg.QtGui.QColor(255, 255, 255, 200))

        # paint colorbar
        p.drawPicture(0, 0, self.pic)
