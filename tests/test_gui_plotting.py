"""Test of data set functionalities"""
import pathlib

import numpy as np
from PyQt5 import QtCore
import pytest
from shapeout2.gui.main import ShapeOut2
from shapeout2 import pipeline, session


datapath = pathlib.Path(__file__).parent / "data"


@pytest.fixture(autouse=True)
def run_around_tests():
    # Code that will run before your test, for example:
    session.clear_session()
    # A test function will be run at this point
    yield
    # Code that will run after your test, for example:
    session.clear_session()


def test_handle_axis_selection_empty_plot(qtbot):
    """User did not add a dataset to a plot and starts changing plot params"""
    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # add a dataslot
    path = datapath / "calibration_beads_47.rtdc"
    mw.add_dataslot(paths=[path])

    # add a plot
    plot_id = mw.add_plot()

    assert len(mw.pipeline.slot_ids) == 1, "we added that"
    assert len(mw.pipeline.filter_ids) == 1, "automatically added"
    assert len(mw.pipeline.plot_ids) == 1, "we added that"

    # activate analysis view
    pe = mw.block_matrix.get_widget(filt_plot_id=plot_id)
    qtbot.mouseClick(pe.toolButton_modify, QtCore.Qt.LeftButton)

    pv = mw.widget_ana_view.widget_plot

    # This lead to:
    #    Traceback (most recent call last):
    #  File "/ShapeOut2/shapeout2/gui/analysis/ana_plot.py",
    #     line 406, in on_axis_changed
    #    self._set_contour_spacing_auto(axis_y=gen["axis y"])
    #  File "/ShapeOut2/shapeout2/gui/analysis/ana_plot.py",
    #     line 361, in _set_contour_spacing_auto
    #    spacings_xy.append(np.min(spacings))
    #  File "/numpy/core/fromnumeric.py", line 2618, in amin
    #    initial=initial)
    #  File "/numpy/core/fromnumeric.py", line 86, in _wrapreduction
    #    return ufunc.reduce(obj, axis, dtype, out, **passkwargs)
    # ValueError: zero-size array to reduction operation minimum which
    # has no identity
    pv.comboBox_axis_y.setCurrentIndex(pv.comboBox_axis_y.findData("emodulus"))


def test_handle_empty_plots_issue_27(qtbot):
    """Correctly handle empty plots

    https://github.com/ZELLMECHANIK-DRESDEN/ShapeOut2/issues/27
    """
    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # add a dataslot
    path = datapath / "calibration_beads_47.rtdc"
    mw.add_dataslot(paths=[path])
    # add another one
    mw.add_dataslot(paths=[path])

    assert len(mw.pipeline.slot_ids) == 2, "we added those"
    assert len(mw.pipeline.filter_ids) == 1, "automatically added"

    # activate a dataslot
    slot_id = mw.pipeline.slot_ids[0]
    filt_id = mw.pipeline.filter_ids[0]
    em = mw.block_matrix.get_widget(slot_id, filt_id)
    qtbot.mouseClick(em, QtCore.Qt.LeftButton)  # activate
    # did that work?
    assert mw.pipeline.is_element_active(slot_id, filt_id)

    # filter away all events
    fe = mw.block_matrix.get_widget(filt_plot_id=filt_id)
    qtbot.mouseClick(fe.toolButton_modify, QtCore.Qt.LeftButton)
    fv = mw.widget_ana_view.widget_filter
    qtbot.mouseClick(fv.toolButton_moreless, QtCore.Qt.LeftButton)
    rc = fv._box_range_controls["area_um"]
    qtbot.mouseClick(rc.checkBox, QtCore.Qt.LeftButton)
    # did that work?
    assert rc.checkBox.isChecked()
    qtbot.mouseClick(fv.toolButton_moreless, QtCore.Qt.LeftButton)
    # set range
    rc.doubleSpinBox_min.setValue(0)
    rc.doubleSpinBox_max.setValue(1)
    qtbot.mouseClick(fv.pushButton_apply, QtCore.Qt.LeftButton)
    # did that work?
    ds = mw.pipeline.get_dataset(slot_index=0, filt_index=0,
                                 apply_filter=True)
    assert np.sum(ds.filter.all) == 0

    # now create a plot window
    plot_id = mw.add_plot()
    pe = mw.block_matrix.get_widget(slot_id, plot_id)
    with pytest.warns(pipeline.core.EmptyDatasetWarning):
        # this now only throws a warning
        qtbot.mouseClick(pe, QtCore.Qt.LeftButton)  # activate (raises #27)


def test_handle_nan_valued_feature_color(qtbot):
    """User wants to color scatter data points with feature containing nans"""
    spath = datapath / "version_2_1_2_plot_color_emodulus.so2"

    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # lead to:
    # OverflowError: argument 4 overflowed: value must be in the range
    # -2147483648 to 2147483647
    mw.on_action_open(spath)


def test_remove_plots_issue_36(qtbot):
    """Correctly handle empty plots

    https://github.com/ZELLMECHANIK-DRESDEN/ShapeOut2/issues/36

    Traceback (most recent call last):
      File "/home/paul/repos/ShapeOut2/shapeout2/gui/main.py",
        line 193, in adopt_pipeline
        lay = pipeline_state["plots"][plot_index]["layout"]
    IndexError: list index out of range
    """
    mw = ShapeOut2()
    qtbot.addWidget(mw)

    # add a dataslots
    path = datapath / "calibration_beads_47.rtdc"
    mw.add_dataslot(paths=[path, path, path])

    assert len(mw.pipeline.slot_ids) == 3, "we added those"
    assert len(mw.pipeline.filter_ids) == 1, "automatically added"

    # now create a plot window
    plot_id = mw.add_plot()
    # and another one
    mw.add_plot()

    # remove a plot
    pw = mw.block_matrix.get_widget(filt_plot_id=plot_id)
    pw.action_remove()
