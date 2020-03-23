import itertools
import pathlib
import shutil
import tempfile

import h5py
import numpy as np
from shapeout2 import pipeline, session


def equal_state(a, b):
    """Compares dictionaries recursively

    - nan-values are allowed
    """
    if isinstance(a, dict):
        equal = True
        for key in a:
            equal &= equal_state(a[key], b[key])
    elif isinstance(a, list):
        equal = True
        for ai, bi in zip(a, b):
            equal &= equal_state(ai, bi)
    elif isinstance(a, float):
        if np.isnan(a):
            equal = np.isnan(b)
        else:
            equal = not np.isnan(a)
    else:
        equal = a == b
    return equal


def make_pipeline(nslots=2, nfilters=3, nplots=1, paths=None):
    """Create a sample pipeline

    - Each filter has a different box filter
    - Every other filter/plot will be set active
    """
    if paths is None:
        here = pathlib.Path(__file__).parent
        paths = [here / "data" / "calibration_beads_47.rtdc"]

    # circular iterator over paths
    pathcycle = itertools.cycle(paths)

    # initiate the pipeline
    pl = pipeline.Pipeline()

    for _ in range(nslots):
        pl.add_slot(path=next(pathcycle))

    feats = pl.get_features(scalar=True)

    for jj in range(nfilters):
        filt_id = pl.add_filter()
        filt = pl.get_filter(filt_id)

        feat = feats[jj]
        fmin, fmax = pl.get_min_max(feat)
        # modify the filter
        filt.boxdict[filt_id] = {"start": fmin,
                                 "end": (fmin + fmax)/2,
                                 "active": True}

    # set every other filter active
    active = True
    for slot_id in pl.slot_ids:
        for filt_id in pl.filter_ids:
            pl.set_element_active(slot_id, filt_id, active)
            active = not active

    # add a plot
    for _ in range(nplots):
        pl.add_plot()

    # set every other plot active
    active = True
    for slot_id in pl.slot_ids:
        for plot_id in pl.plot_ids:
            pl.set_element_active(slot_id, plot_id, active)
            active = not active

    return pl


def test_2_1_1_new_key_emodulus_enabled():
    """In Shape-Out 2.1.1 we introduces the "emodulus enabled" key

    If it is disabled (reservoir measurements), then the emodulus
    analysis options are not shown in the Slot options. See also
    changes made in dclab 0.22.4 (test for reservoir existence).
    """
    spath = pathlib.Path(__file__).parent / "data" / "version_2_1_0_basic.so2"
    pl = session.open_session(spath)
    sc = pl.slots[0].config
    assert "emodulus" in sc
    assert "emodulus enabled" in sc["emodulus"]
    assert sc["emodulus"]["emodulus enabled"]


def test_file_hash():
    tempdir = pathlib.Path(tempfile.mkdtemp(prefix="test_shapeout2_session_"))
    # custom path to measurement
    p0 = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"
    pp = tempdir / "calibration_beads_47.rtdc"
    shutil.copy(p0, pp)
    hash1 = session.hash_file_partially(pp)
    session.hash_file_partially.cache_clear()  # force recomputation of hashes
    # modify the file
    with h5py.File(pp, mode="a") as h5:
        h5.attrs["setup:medium"] = "unknown"
    hash2 = session.hash_file_partially(pp)
    assert hash1 != hash2
    # cleanup
    shutil.rmtree(tempdir, ignore_errors=True)


def test_missing_path_in_session():
    tempdir = pathlib.Path(tempfile.mkdtemp(prefix="test_shapeout2_session_"))
    spath = tempdir / "session.so2"
    # custom path to measurement
    p0 = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"
    pp = tempdir / "calibration_beads_47.rtdc"
    shutil.copy(p0, pp)
    pl = make_pipeline(paths=[pp])
    session.save_session(spath, pl)
    session.clear_session(pl)
    # rename the file
    pc = pp.with_name("calibration_beads_47_moved.rtdc")
    pp.rename(pc)
    # load bad session
    try:
        session.open_session(spath)
    except session.DataFileNotFoundError as e:
        assert pp in e.missing_paths
    else:
        assert False, "should have raised an error!"
    # try again with proper search path
    pl3 = session.open_session(spath, search_paths=[pc])
    session.clear_session(pl3)
    # try again with a directory as search path
    other = tempdir / "other"
    other.mkdir()
    pc.rename(other / pp.name)  # must have same name as `pp`
    pl4 = session.open_session(spath, search_paths=[other])
    session.clear_session(pl4)
    # cleanup
    shutil.rmtree(tempdir, ignore_errors=True)


def test_relative_paths():
    tempdir = pathlib.Path(tempfile.mkdtemp(prefix="test_shapeout2_session_"))
    # custom path for data
    p0 = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"
    datadir = tempdir / "data"
    datadir.mkdir()
    pp = datadir / "calibration_beads_47.rtdc"
    shutil.copy(p0, pp)
    # custom path for session
    sessiondir = tempdir / "session"
    sessiondir.mkdir()
    spath = sessiondir / "session.so2"
    # pipeline
    pl = make_pipeline(paths=[pp])
    session.save_session(spath, pl)
    session.clear_session(pl)
    # new session directory
    new_sessiondir = tempdir / "new" / "path" / "abracadabra"
    new_sessiondir.mkdir(parents=True)
    new_spath = new_sessiondir / spath.name
    spath.rename(new_spath)
    # new path directory (same relative path)
    new_datadir = tempdir / "new" / "path" / "data"
    new_datadir.mkdir(parents=True)
    new_pp = new_datadir / pp.name
    pp.rename(new_pp)
    # and load it (without search_paths as arguments)
    session.open_session(new_spath)
    # cleanup
    shutil.rmtree(tempdir, ignore_errors=True)


def test_simple_save_open_session():
    pl = make_pipeline()
    old_state = pl.__getstate__()

    tempdir = pathlib.Path(tempfile.mkdtemp(prefix="test_shapeout2_session_"))
    spath = tempdir / "session.so2"

    session.save_session(spath, pl)

    # currently, there may only be one pipeline
    session.open_session(spath, pl)
    new_state = pl.__getstate__()

    assert equal_state(old_state, new_state)

    # test opposite
    old_state["slots"][0]["emodulus"]["emodulus temperature"] = 10
    assert not equal_state(old_state, new_state)
    # cleanup
    shutil.rmtree(tempdir, ignore_errors=True)


def test_wrong_hash():
    tempdir = pathlib.Path(tempfile.mkdtemp(prefix="test_shapeout2_session_"))
    spath = tempdir / "session.so2"
    # custom path to measurement
    p0 = pathlib.Path(__file__).parent / "data" / "calibration_beads_47.rtdc"
    pp = pathlib.Path(tempdir) / "calibration_beads_47.rtdc"
    shutil.copy(p0, pp)
    pl = make_pipeline(paths=[pp])
    session.save_session(spath, pl)
    session.clear_session(pl)  # clear session before opening h5 file rw
    session.hash_file_partially.cache_clear()  # force recomputation of hashes
    # modify the file
    with h5py.File(pp, mode="a") as h5:
        h5.attrs["setup:medium"] = "unknown"
    # opening modified file should just work if the path matches
    pl2 = session.open_session(spath)
    session.clear_session(pl2)
    # but when the directory changes, the hash is checked
    other = tempdir / "other"
    other.mkdir()
    pp.rename(other / pp.name)
    try:
        session.open_session(spath, search_paths=[other])
    except session.DataFileNotFoundError as e:
        assert pp in e.missing_paths
    else:
        assert False, "should have raised an error!"
    # cleanup
    shutil.rmtree(tempdir, ignore_errors=True)


if __name__ == "__main__":
    # Run all tests
    loc = locals()
    for key in list(loc.keys()):
        if key.startswith("test_") and hasattr(loc[key], "__call__"):
            loc[key]()
