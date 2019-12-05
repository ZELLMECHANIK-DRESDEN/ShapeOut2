import pathlib

from shapeout2 import pipeline


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
