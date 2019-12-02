import json
import os
import pathlib
import shutil
import tempfile
import zipfile

import dclab

from .pipeline import Dataslot, Filter, Plot
from ._version import version


class PathlibJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, pathlib.Path):
            return {"__type__": "path",
                    "__data__": o.as_posix()
                    }
        # Let the base class default method raise the TypeError
        return super(PathlibJSONEncoder, self).default(o)


class PathlibJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super(PathlibJSONDecoder, self).__init__(object_hook=self.object_hook,
                                                 *args, **kwargs)

    def object_hook(self, obj):
        if "__type__" in obj and obj["__type__"] == "path":
            return pathlib.Path(obj["__data__"])
        return obj


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


def import_filters(path, pipeline, strict=False):
    """Load filters from a JSON file into a pipeline

    Parameters
    ----------
    path: pathlib.Path or str
        Path to the filter file
    pipeline: shapeout2.pipeline.Pipeline
        Analysis pipeline to import filters to
    strict: bool
        If False (default), new filter identifiers are created
        for each filter. If True, the given filter identifiers
        will be used - Raises a ValueError if the filter exists.
        For loading filters into a pipeline, this should be False.
        For loading session filters, this should be True.
    """
    path = pathlib.Path(path)
    if path.suffix == ".poly":
        # add a new polygon filter
        dclab.PolygonFilter.import_all(path)
    elif path.suffix == ".sof":
        dump = path.read_text()
        dump_state = json.loads(dump)
        # add polygon filters from file
        if not strict:
            pf_dict = {}  # maps old to new identifiers
        for pstate in dump_state["polygon filters"]:
            pf = dclab.PolygonFilter(axes=(pstate["axis x"], pstate["axis y"]),
                                     points=pstate["points"])
            pid = pstate["identifier"]
            if not strict:
                # keep track of old and new identifiers
                pf_dict[pid] = pf.unique_id
            if pid != pf.unique_id:
                if strict:
                    if dclab.PolygonFilter.unique_id_exists(pid):
                        raise ValueError("PolygonFilter with unique_id "
                                         + "{} already exists!".format(pid))
                    else:
                        # change the unique_id to that of the original filter
                        pf._set_unique_id(pid)
                else:
                    # use the unique_id of the newly-created filter
                    pstate["identifier"] = pf.unique_id
            pf.__setstate__(pstate)
        # add a new filter set
        for state in dump_state["filters"]:
            if strict:
                filt = Filter(identifier=state["identifier"])
            else:
                filt = Filter()
                state["identifier"] = filt.identifier
                # transform original polygon filter ids
                newpids = [pf_dict[pid] for pid in state["polygon filters"]]
                state["polygon filters"] = newpids
            filt.__setstate__(state)
            pipeline.add_filter(filt=filt)
    else:
        raise ValueError("Unrecognized file extension "
                         + "'{}' for filters.".format(path.suffix))


def save_session(path, pipeline):
    """Save an entire pipeline session"""
    path = pathlib.Path(path)
    tempdir = pathlib.Path(tempfile.mkdtemp(prefix="ShapeOut2-session-save_"))
    # filters
    export_filters(tempdir / "filters.sof", pipeline)
    # slots
    for ii, slot in enumerate(pipeline.slots):
        sdump = json.dumps(slot.__getstate__(),
                           cls=PathlibJSONEncoder,
                           sort_keys=True,
                           indent=2)
        (tempdir / "slot_{}.json".format(ii)).write_text(sdump)
    # plots
    for jj, plot in enumerate(pipeline.plots):
        pdump = json.dumps(plot.__getstate__(),
                           sort_keys=True,
                           indent=2)
        (tempdir / "plot_{}.json".format(jj)).write_text(pdump)
    # pipeline block matrix
    mdump = json.dumps(pipeline.element_states,
                       sort_keys=True,
                       indent=2)
    (tempdir / "matrix.json").write_text(mdump)
    # additional information
    search_paths = {}
    for slot in pipeline.slots:
        try:
            rel = os.path.relpath(slot.path, path.parent)
        except (OSError, ValueError):
            rel = "."
        search_paths[slot.identifier] = rel
    remarks = {"search paths": search_paths,
               "version": version,
               }
    rdump = json.dumps(remarks,
                       cls=PathlibJSONEncoder,
                       sort_keys=True,
                       indent=2)
    (tempdir / "remarks.json").write_text(rdump)
    # zip everything
    with zipfile.ZipFile(path, mode='w') as arc:
        for pp in tempdir.rglob("*"):
            if pp.is_file():
                arc.write(pp, pp.relative_to(tempdir))
    # cleanup
    shutil.rmtree(str(tempdir), ignore_errors=True)


def clear_session(pipeline):
    """Clear the entire analysis pipeline"""
    # reset the pipeline
    pipeline.reset()
    # remove any existing filters, plots, or slots
    for cls in [Dataslot, Filter, Plot]:
        cls._instance_counter = 0
        cls._instances = {}
    # remove polygon filters
    dclab.PolygonFilter.instances = []
    dclab.PolygonFilter._instance_counter = 0


def open_session(path, pipeline, search_paths={}):
    """Load a session (optionally overriding an existing pipeline)

    Parameters
    ----------
    path: pathlib.Path or str
        Path to the session file
    pipeline: shapeout2.pipeline.Pipeline
        The pipeline will be reset before loading anything
    search_paths: dict
        Search path for each slot (slot identifiers as keys).
    """
    clear_session(pipeline)
    # extract the session data
    tempdir = tempfile.mkdtemp(prefix="ShapeOut2-session-open_")
    tempdir = pathlib.Path(tempdir)
    with zipfile.ZipFile(path, mode='r') as arc:
        arc.extractall(tempdir)
    # load filters
    import_filters(tempdir / "filters.sof", pipeline, strict=True)
    # load slots
    slotpaths = sorted(tempdir.glob("slot_*.json"),
                       key=lambda x: int(x.name[5:-5]))  # according to index
    for sp in slotpaths:
        sstate = json.loads(sp.read_text(),
                            cls=PathlibJSONDecoder)
        slot = Dataslot(identifier=sstate["identifier"],
                        path=sstate["path"])
        slot.__setstate__(sstate)
        pipeline.add_slot(slot)
    # load plots
    plotpaths = sorted(tempdir.glob("plot_*.json"),
                       key=lambda x: int(x.name[5:-5]))  # according to index
    for pp in plotpaths:
        pstate = json.loads(pp.read_text())
        plot = Plot(identifier=pstate["identifier"])
        plot.__setstate__(pstate)
        pipeline.add_plot(plot)
    # load element states
    estates = json.loads((tempdir / "matrix.json").read_text())
    pipeline.element_states = estates
