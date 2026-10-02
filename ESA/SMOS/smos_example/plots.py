"""Plotting utilities for SMOS Level-2 swath retrievals.

The products arrive as scattered points on the ISEA 4H9 grid, so the map
is a scatter plot of grid-point positions rather than an image.

This is example code from the book
`Earth Observation in Practice <https://tinyurl.com/43e26by6>`_.

Author: Edward Hartnett
Date: 2026-10-02
"""

from pathlib import Path

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

#: Per-variable display defaults: (colormap, vmin, vmax, colorbar label).
VARIABLE_STYLES = {
    "Soil_Moisture": ("YlGnBu", 0.0, 0.7, "Soil moisture (m³/m³)"),
    "SSS_corr": ("viridis", 30.0, 40.0, "Sea surface salinity (PSU)"),
    "Sea_Surface_Salinity": ("viridis", 30.0, 40.0, "Sea surface salinity (PSU)"),
}


def _finish(fig, out_path: Path | None, show: bool) -> Path | None:
    """Save ``fig`` to ``out_path`` (if given), optionally show it, then close it.

    Returns the path written, or ``None`` when no file was requested.
    """
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    return out_path


def _style(da: xr.DataArray) -> tuple[str, float, float, str]:
    """Pick colormap, range, and colorbar label for a variable.

    Known SMOS variables get physical ranges; anything else uses the
    2nd-98th percentile of the data so unknown variables still plot.
    """
    if da.name in VARIABLE_STYLES:
        return VARIABLE_STYLES[da.name]
    valid = da.values[np.isfinite(da.values)]
    vmin, vmax = (float(np.percentile(valid, 2)), float(np.percentile(valid, 98))) \
        if valid.size else (0.0, 1.0)
    units = da.attrs.get("units", "")
    label = da.attrs.get("long_name", da.name)
    return "viridis", vmin, vmax, f"{label} ({units})" if units else label


def plot_map(
    da: xr.DataArray,
    out_path: Path | None = None,
    show: bool = False,
    pad: float = 5.0,
) -> Path | None:
    """Plot a Level-2 swath as a colored scatter of grid points.

    The map extent follows the data (with *pad* degrees of margin);
    points outside valid range are dropped by the colormap limits.
    """
    cmap, vmin, vmax, label = _style(da)
    lon = da["lon"].values
    lat = da["lat"].values
    finite = np.isfinite(da.values)

    west = max(-180.0, float(np.nanmin(lon)) - pad)
    east = min(180.0, float(np.nanmax(lon)) + pad)
    south = max(-90.0, float(np.nanmin(lat)) - pad)
    north = min(90.0, float(np.nanmax(lat)) + pad)

    fig, ax = plt.subplots(
        figsize=(8, 8), subplot_kw={"projection": ccrs.PlateCarree()}
    )
    ax.set_extent([west, east, south, north], crs=ccrs.PlateCarree())
    sc = ax.scatter(
        lon[finite], lat[finite], c=da.values[finite],
        s=2, cmap=cmap, vmin=vmin, vmax=vmax,
        transform=ccrs.PlateCarree(), linewidths=0,
    )
    ax.coastlines(resolution="50m", linewidth=0.6)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="gray", alpha=0.5)
    gl.top_labels = gl.right_labels = False
    fig.colorbar(sc, ax=ax, shrink=0.7, pad=0.03, label=label)
    title = da.attrs.get("title", "SMOS Level-2")
    start = da.attrs.get("time_coverage_start", "")[:16]
    ax.set_title(f"{title}\n{da.attrs.get('long_name', da.name)} {start}".strip())
    return _finish(fig, out_path, show)


def plot_histogram(
    da: xr.DataArray, out_path: Path | None = None, show: bool = False
) -> Path | None:
    """Plot a histogram of the valid retrieval values."""
    valid = da.values[np.isfinite(da.values)]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(valid, bins=100, color="steelblue", edgecolor="none")
    units = da.attrs.get("units", "")
    xlabel = da.attrs.get("long_name", da.name)
    ax.set_xlabel(f"{xlabel} ({units})" if units else xlabel)
    ax.set_ylabel("grid points")
    ax.set_title(f"{da.name}: {valid.size} valid retrievals")
    return _finish(fig, out_path, show)
