"""Plotting utilities for MODIS fields.

This is example code from the book
`Earth Observation in Practice <https://tinyurl.com/43e26by6>`_.

Author: Edward Hartnett
Date: 2026-10-02
"""

from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np

from .reader import ModisField


def _finish(fig, out_path: Path | None, show: bool) -> Path | None:
    """Save ``fig`` to ``out_path`` (if given), optionally show it, then close it."""
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return out_path


def _label(field: ModisField) -> str:
    """Colorbar label: long name plus units, when units are meaningful."""
    if field.units and field.units.lower() != "none":
        return f"{field.long_name} ({field.units})"
    return field.long_name


def _limits(field: ModisField) -> tuple[float, float]:
    """Color limits from the 2nd and 98th percentiles of the valid data."""
    valid = field.data.compressed()
    if valid.size == 0:
        return 0.0, 1.0
    return tuple(float(v) for v in np.percentile(valid, [2, 98]))


def plot_map(field: ModisField, out_path: Path | None = None,
             show: bool = False) -> Path | None:
    """Plot a geolocated field on a map.

    Polar granules (mean latitude beyond 60 degrees) use a polar
    stereographic projection; everything else uses PlateCarree.
    """
    if field.lat is None or field.lon is None:
        raise ValueError(f"{field.name} has no geolocation")
    mean_lat = float(np.nanmean(field.lat))
    if mean_lat > 60.0:
        proj = ccrs.NorthPolarStereo(central_longitude=float(np.nanmedian(field.lon)))
    elif mean_lat < -60.0:
        proj = ccrs.SouthPolarStereo(central_longitude=float(np.nanmedian(field.lon)))
    else:
        proj = ccrs.PlateCarree(central_longitude=float(np.nanmedian(field.lon)))

    lon = np.ma.masked_invalid(field.lon)
    lat = np.ma.masked_invalid(field.lat)
    data = np.ma.masked_where(lon.mask | lat.mask, field.data)
    vmin, vmax = _limits(field)

    fig, ax = plt.subplots(figsize=(9, 8), subplot_kw={"projection": proj})
    mesh = ax.pcolormesh(np.ma.filled(lon, 0.0), np.ma.filled(lat, 0.0), data,
                         cmap="viridis", vmin=vmin, vmax=vmax, shading="auto",
                         transform=ccrs.PlateCarree())
    ax.set_extent([float(lon.min()), float(lon.max()), float(lat.min()), float(lat.max())],
                  crs=ccrs.PlateCarree())
    ax.coastlines(resolution="50m", linewidth=0.6)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="gray", alpha=0.5)
    gl.top_labels = gl.right_labels = False
    fig.colorbar(mesh, ax=ax, shrink=0.7, pad=0.06, label=_label(field))
    ax.set_title(f"{field.name}\n{field.granule}", fontsize=10)
    return _finish(fig, out_path, show)


def plot_array(field: ModisField, out_path: Path | None = None,
               show: bool = False) -> Path | None:
    """Plot a field in its native row/column (scan line, pixel) space."""
    vmin, vmax = _limits(field)
    fig, ax = plt.subplots(figsize=(8, 9))
    im = ax.imshow(field.data, cmap="viridis", vmin=vmin, vmax=vmax,
                   interpolation="nearest")
    ax.set_xlabel("pixel (column)")
    ax.set_ylabel("line (row)")
    fig.colorbar(im, ax=ax, shrink=0.7, label=_label(field))
    ax.set_title(f"{field.name} (array space)\n{field.granule}", fontsize=10)
    return _finish(fig, out_path, show)
