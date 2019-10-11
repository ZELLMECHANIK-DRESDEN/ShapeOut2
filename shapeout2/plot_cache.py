"""Facilitate caching of plot data"""
from . import util


def get_scatter_data(rtdc_ds, downsample, xax, yax, xscale, yscale,
                     kde_type="histogram", kde_kwargs={}):
    tohash = [rtdc_ds.identifier, rtdc_ds.filter.all, downsample,
              xax, yax, xscale, yscale,
              kde_type, kde_kwargs]
    shash = util.hashobj(tohash)

    if shash in cache_data:
        x, y, kde, idx = cache_data[shash]
    else:
        rtdc_ds.apply_filter()
        # compute scatter plot data
        x, y, idx = rtdc_ds.get_downsampled_scatter(
            xax=xax,
            yax=yax,
            downsample=downsample,
            xscale=xscale,
            yscale=yscale,
            remove_invalid=True,
            ret_mask=True)
        # kde
        kde = rtdc_ds.get_kde_scatter(
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
