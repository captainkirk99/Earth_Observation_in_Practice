"""Plotting utilities for gridded VIIRS LST subsets."""

from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import xarray as xr


def _finish(fig, out_path: Path | None, show: bool) -> Path | None:
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    return out_path


def plot_lst_map(
    lst: xr.DataArray,
    out_path: Path | None = None,
    show: bool = False,
    vmin: float = 15.0,
    vmax: float = 50.0,
) -> Path | None:
    """Plot an LST subset in degrees Celsius on a PlateCarree map.

    Masked (cloud, water, bad quality) pixels are left transparent.
    """
    fig, ax = plt.subplots(
        figsize=(8, 9), subplot_kw={"projection": ccrs.PlateCarree()}
    )
    mesh = ax.pcolormesh(
        lst["lon"],
        lst["lat"],
        lst.values - 273.15,
        cmap="inferno",
        vmin=vmin,
        vmax=vmax,
        shading="auto",
        transform=ccrs.PlateCarree(),
    )
    ax.coastlines(resolution="10m", linewidth=0.6)
    ax.add_feature(cfeature.STATES.with_scale("10m"), linewidth=0.5)
    ax.add_feature(cfeature.LAKES.with_scale("10m"), facecolor="none", edgecolor="steelblue", linewidth=0.4)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="gray", alpha=0.5)
    gl.top_labels = gl.right_labels = False
    fig.colorbar(mesh, ax=ax, shrink=0.7, pad=0.03, label="Land surface temperature (°C)")
    start = lst.attrs.get("time_coverage_start", "")[:10]
    ax.set_title(
        f"{lst.attrs.get('platform', 'JPSS')} VIIRS gridded {lst.attrs.get('long_name', 'LST')}\n{start}"
    )
    return _finish(fig, out_path, show)


def plot_footprint(
    lst: xr.DataArray, out_path: Path | None = None, show: bool = False, pad: float = 8.0
) -> Path | None:
    """Plot the subset bounding box on a padded regional map."""
    west, east = float(lst["lon"].min()), float(lst["lon"].max())
    south, north = float(lst["lat"].min()), float(lst["lat"].max())
    fig, ax = plt.subplots(
        figsize=(8, 6), subplot_kw={"projection": ccrs.PlateCarree()}
    )
    ax.set_extent([west - pad, east + pad, south - pad, north + pad], crs=ccrs.PlateCarree())
    ax.coastlines(resolution="50m")
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.5)
    ax.add_feature(cfeature.STATES.with_scale("50m"), linewidth=0.3)
    ax.plot(
        [west, east, east, west, west],
        [south, south, north, north, south],
        color="red",
        linewidth=2,
        transform=ccrs.PlateCarree(),
    )
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="gray", alpha=0.5)
    gl.top_labels = gl.right_labels = False
    ax.set_title("Subset footprint")
    return _finish(fig, out_path, show)
