import pathlib

import dclab
import numpy as np
from shapeout2 import pipeline


def test_apply_filter_ray():
    path = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"

    # initiate the pipeline
    pl = pipeline.Pipeline()
    slot_id = pl.add_slot(path=path)

    # add a filter
    filt_id1 = pl.add_filter()
    filt1 = pl.get_filter(filt_id1)
    amin, amax = pl.get_min_max("area_um")
    filt1.boxdict["area_um"] = {"start": amin,
                                "end": (amin + amax)/2,
                                "active": True}
    pl.set_element_active(slot_id, filt_id1)

    # and another one
    filt_id2 = pl.add_filter()
    filt2 = pl.get_filter(filt_id2)
    dmin, dmax = pl.get_min_max("deform")
    filt2.boxdict["deform"] = {"start": dmin,
                               "end": (dmin + dmax)/2,
                               "active": True}
    pl.set_element_active(slot_id, filt_id2)

    ds_ref = pl.get_dataset(0)  # this will run through the filter ray
    ds0 = dclab.new_dataset(path)
    ds_ext = pl.apply_filter_ray(ds0, slot_id)  # this should do the same thing

    for feat in ds_ref.features_loaded:
        if feat in dclab.dfn.scalar_feature_names:
            assert np.allclose(ds_ref[feat], ds_ext[feat]), feat
    assert np.all(ds_ref.filter.all == ds_ext.filter.all)


def test_get_min_max_plot():
    """See #22"""
    path = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"

    # initiate the pipeline
    pl = pipeline.Pipeline()
    slot_id = pl.add_slot(path=path)

    # add a filter
    filt_id = pl.add_filter()
    filt = pl.get_filter(filt_id)

    # get the current min/max values
    amin, amax = pl.get_min_max("area_um")

    # modify the filter
    filt.boxdict["area_um"] = {"start": amin,
                               "end": (amin + amax)/2,
                               "active": True}

    # make the filter active in the filter ray
    pl.set_element_active(slot_id, filt_id)

    # add a plot
    plot_id = pl.add_plot()
    pl.set_element_active(slot_id, plot_id)

    # get the new min/max values
    amin2, amax2 = pl.get_min_max("area_um", plot_id=plot_id)

    assert amin == amin2
    assert amax2 <= (amin + amax) / 2


if __name__ == "__main__":
    # Run all tests
    loc = locals()
    for key in list(loc.keys()):
        if key.startswith("test_") and hasattr(loc[key], "__call__"):
            loc[key]()
