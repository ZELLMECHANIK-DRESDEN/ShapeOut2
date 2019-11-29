import json
import pathlib

import dclab

from .pipeline import Filter


def export_filters(path, pipeline, filt_ids=None):
    """Export filters of a pipeline to a JSON file"""
    if filt_ids is None:
        filt_ids = pipeline.filter_ids
    # First, get all relevant polygon filters
    polyids = set([])
    for filt in pipeline.filters:
        if filt.identifier in filt_ids:
            polyids |= set(filt.polylist)
    poly_states = []
    for pid in sorted(polyids):
        pf = dclab.PolygonFilter.get_instance_from_id(pid)
        poly_states.append(pf.__getstate__())
    # Then, get the remaining filter settings
    filt_states = []
    for filt in pipeline.filters:
        if filt.identifier in filt_ids:
            filt_states.append(filt.__getstate__())
    state = {"polygon filters": poly_states,
             "filters": filt_states}
    dump = json.dumps(state, sort_keys=True, indent=2)
    pathlib.Path(path).write_text(dump)


def import_filters(path, pipeline):
    """Load filters from a JSON file into a pipeline"""
    path = pathlib.Path(path)
    if path.suffix == ".poly":
        # add a new polygon filter
        dclab.PolygonFilter.import_all(path)
    elif path.suffix == ".sof":
        dump = path.read_text()
        dump_state = json.loads(dump)
        # add polygon filters from file
        pf_dict = {}  # maps old to new identifiers
        for pstate in dump_state["polygon filters"]:
            pf = dclab.PolygonFilter(axes=(pstate["axis x"], pstate["axis y"]),
                                     points=pstate["points"])
            pf_dict[pstate["identifier"]] = pf.unique_id
            pstate["identifier"] = pf.unique_id
            pf.__setstate__(pstate)
        # add a new filter set
        for state in dump_state["filters"]:
            filt = Filter()
            state["identifier"] = filt.identifier
            newpids = [pf_dict[pid] for pid in state["polygon filters"]]
            state["polygon filters"] = newpids
            filt.__setstate__(state)
            pipeline.add_filter(filt=filt)
    else:
        raise ValueError("Unrecognized file extension "
                         + "'{}' for filters.".format(path.suffix))
