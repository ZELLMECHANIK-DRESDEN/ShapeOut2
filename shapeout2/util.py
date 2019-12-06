import hashlib
import numbers
import pathlib

import h5py
import numpy as np


def hashobj(obj):
    """Compute md5 hex-hash of a Python object"""
    return hashlib.md5(obj2str(obj)).hexdigest()


def obj2str(obj):
    """String representation of an object for hashing"""
    if isinstance(obj, str):
        return obj.encode("utf-8")
    elif isinstance(obj, pathlib.Path):
        return obj2str(str(obj))
    elif isinstance(obj, (bool, numbers.Number)):
        return str(obj).encode("utf-8")
    elif obj is None:
        return b"none"
    elif isinstance(obj, np.ndarray):
        return obj.tostring()
    elif isinstance(obj, tuple):
        return obj2str(list(obj))
    elif isinstance(obj, list):
        return b"".join(obj2str(o) for o in obj)
    elif isinstance(obj, dict):
        return obj2str(sorted(obj.items()))
    elif hasattr(obj, "identifier"):
        return obj2str(obj.identifier)
    elif isinstance(obj, h5py.Dataset):
        return obj2str(obj[0])
    else:
        raise ValueError("No rule to convert object '{}' to string.".
                         format(obj.__class__))
