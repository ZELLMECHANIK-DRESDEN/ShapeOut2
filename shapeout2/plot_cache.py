"""Facilitate caching of plot data"""
import dclab

from . import filter
from . import util


def get_scatter_data(path, filters, downsample, xax, yax, xscale, yscale,
                     kde_type="histogram", kde_kwargs={}):
    tohash = [path, downsample, xax, yax, xscale, yscale, kde_type, kde_kwargs]
    # compute filter hash
    for fkey in filters:  # order matters
        finst = filter.Filter.get_filter(identifier=fkey)
        tohash.append(finst.hash)
    shash = util.hashobj(tohash)

    if shash in cache_data:
        x, y, kde, idx = cache_data[shash]
    else:
        with dclab.new_dataset(path) as ds:
            # apply filters
            for fkey in filters:
                finst = filter.Filter.get_filter(identifier=fkey)
                ds = finst.apply_to(ds)
            # compute scatter plot data
            x, y, idx = ds.get_downsampled_scatter(
                xax=xax,
                yax=yax,
                downsample=downsample,
                xscale=xscale,
                yscale=yscale,
                remove_invalid=True,
                ret_mask=True)
            # kde
            kde = ds.get_kde_scatter(
                xax=xax,
                yax=yax,
                positions=(x, y),
                kde_type=kde_type,
                kde_kwargs=kde_kwargs,
                xscale=xscale,
                yscale=yscale)
            # save in cache
            cache_data[shash] = x, y, kde, idx
    return x, y, kde, idx


cache_data = {}
