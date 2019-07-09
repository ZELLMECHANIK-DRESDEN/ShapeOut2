"""Facilitate caching of plot data"""
import dclab

from . import filter
from . import util


def get_downsampled_scatter(path, filters, downsample, xax, yax,
                            xscale, yscale):
    tohash = [path, downsample, xax, yax, xscale, yscale]
    # compute filter hash
    for fkey in filters:  # order matters
        finst = filter.Filter.get_filter(identifier=fkey)
        tohash.append(finst.hash)
    shash = util.hashobj(tohash)

    if shash in cache_data:
        x, y = cache_data[shash]
    else:
        with dclab.new_dataset(path) as ds:
            # apply filters
            for fkey in filters:
                finst = filter.Filter.get_filter(identifier=fkey)
                ds = finst.apply_to(ds)
            # compute scatter plot data
            x, y = ds.get_downsampled_scatter(
                xax=xax,
                yax=yax,
                downsample=downsample,
                xscale=xscale,
                yscale=yscale)
            if downsample:
                # caching only makes sense when downsampling
                cache_data[shash] = x, y
    return x, y


cache_data = {}
