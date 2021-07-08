import pyqtgraph as pg


class ShapeOutColorBarItem(pg.ColorBarItem):
    def __init__(self, yoffset, height, label, *args, **kwargs):
        """pg.ColorBarItem modified for Shape-Out

        - Added option to define height
        - translate the colorbar so that it is aligned with the plot
        - show the label on the right-hand axis
        - increase the contents margins
        """
        super(ShapeOutColorBarItem, self).__init__(*args, **kwargs)

        for key in ['left', 'top', 'bottom']:
            axis = self.getAxis(key)
            axis.setTicks([])

        # show label on right side
        self.axis.setLabel(label)

        # increase contents margins
        self.layout.setContentsMargins(7, 0, 7, 0)

        # set correct size and position
        self.setFixedHeight(height)

        tr = self.transform()
        tr.translate(0, yoffset)
        self.setTransform(tr)
