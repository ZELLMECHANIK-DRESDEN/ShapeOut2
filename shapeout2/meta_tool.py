"""Convenience methods to retrieve meta data from .rtdc files"""
import functools
import dclab


def get_info(path, section, key):
    config = get_rtdc_config(path)
    return config[section][key]


def get_repr(path, append_path=False):
    """representative string of an RT-DC measurement"""
    exp = get_rtdc_config(path)["experiment"]
    rep = "{} #{} ({} {})".format(exp["sample"],
                                  exp["run index"],
                                  exp["date"],
                                  exp["time"])
    if append_path:
        rep += "\n{}".format(path)
    return rep


@functools.lru_cache(maxsize=None)
def get_rtdc_config(path):
    with dclab.new_dataset(path) as ds:
        config = ds.config.copy()
    return config
