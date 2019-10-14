"""Convenience methods to retrieve meta data from .rtdc files"""
import functools
import dclab


def get_info(path, section, key):
    config = get_rtdc_config(path)
    return config[section][key]


def get_repr(path, append_path=False):
    """representative string of a dataset"""
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
    """Return available features in a dataset"""
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


@functools.lru_cache(maxsize=10000)
def get_rtdc_features_minmax(path, *features):
    """Return dict with min/max of scalar features in a dataset"""
    mmdict = {}
    with dclab.new_dataset(path) as ds:
        for feat in features:
            assert feat in dclab.dfn.scalar_feature_names
            if feat in ds:
                mmdict[feat] = ds[feat].min(), ds[feat].max()
    return mmdict


def get_rtdc_features_minmax_bulk(paths, features=["deform", "area_um"]):
    """Perform `get_rtdc_features_minmax` on a list of paths"""
    mmdict = {}
    for pp in paths:
        mmdi = get_rtdc_features_minmax(pp, *features)
        for feat in mmdi:
            if feat in mmdict:
                fmin = min(mmdict[feat][0], mmdi[feat][0])
                fmax = max(mmdict[feat][1], mmdi[feat][1])
                mmdict[feat] = (fmin, fmax)
            else:
                mmdict[feat] = mmdi[feat]
    return mmdict
