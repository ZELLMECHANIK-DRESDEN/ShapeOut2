from distutils.version import LooseVersion
import pathlib
import warnings

import pyqtgraph as pg


if LooseVersion(pg.__version__) > "0.12.1":
    warnings.warn("New version of pyqtgraph detected! Please remove the "
                  "imageAxisOrder workaround, remove this case structure and "
                  "update setup.py with the new version.")
else:
    # Temporary fix for https://github.com/pyqtgraph/pyqtgraph/issues/1866.
    # Only modifies the AxisItem code in-place. This means that the location
    # has to be writable. For frozen applications, it has to be run before
    # freezing (e.g. during tests).
    axis_item_path = pathlib.Path(pg.graphicsItems.AxisItem.__file__)
    if axis_item_path.suffix == ".py" and axis_item_path.exists():
        lines = axis_item_path.read_text().split("\n")
        for ii, line in enumerate(lines):
            if (line.count("resolves some damn pixel ambiguity")
                    and not line.strip().startswith("#")):
                lines[ii] = "# " + line
                try:
                    axis_item_path.write_text("\n".join(lines))
                except BaseException:
                    warnings.warn("Could not patch AxisItem for ColorBarItem!")


class ShapeOutColorBarItem(pg.ColorBarItem):
    def __init__(self, height, *args, **kwargs):
        """pg.ColorBarItem modified for Shape-Out

        - Workaround for https://github.com/pyqtgraph/pyqtgraph/issues/1720
          which is not in pyqtgraph 0.12.1
        - Added option to define height
        - translate the colorbar so that it is aligned with the plot
        """
        # workaround for pyqtgraph 0.12.1, which does not yet include
        # https://github.com/pyqtgraph/pyqtgraph/issues/1720
        pg.setConfigOption('imageAxisOrder', 'col-major')
        super(ShapeOutColorBarItem, self).__init__(*args, **kwargs)
        pg.setConfigOption('imageAxisOrder', 'row-major')

        for key in ['left', 'top', 'bottom']:
            axis = self.getAxis(key)
            axis.setTicks([])
            axis.translate(-5, 0)
        self.axis.setWidth(45)

        # set correct size and position
        self.setFixedHeight(height)
        self.translate(0, 40)
