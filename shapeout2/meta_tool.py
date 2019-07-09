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


@functools.lru_cache(maxsize=100)
def get_rtdc_config(path):
    with dclab.new_dataset(path) as ds:
        config = ds.config.copy()
    return config


@functools.lru_cache(maxsize=100)
def get_rtdc_features(path, scalar=True):
    """Return available features of a dataset"""
    if scalar:
        features = dclab.dfn.scalar_feature_names
    else:
        features = dclab.dfn.feature_names
    av_feat = []
    with dclab.new_dataset(path) as ds:
        for feat in features:
            if feat in ds:
                av_feat.append(feat)
    return av_feat
