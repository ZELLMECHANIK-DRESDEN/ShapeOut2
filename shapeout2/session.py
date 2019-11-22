import json
import pathlib

import dclab


def export_filters(path, pipeline, filt_ids=None):
    """Export a filters of a pipeline to JSON"""
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
