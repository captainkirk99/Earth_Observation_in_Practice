"""Read ESA SMOS Level-2 products in netCDF format.

The SMOS Level-2 User Data Products are distributed in two formats: the
native Earth Explorer format (``.HDR``/``.DBL`` pairs) and netCDF
(``*.nc``).  This module reads the netCDF versions:

- ``MIR_SMUDP2``: Level-2 soil moisture User Data Product.
- ``MIR_OSUDP2``: Level-2 sea surface salinity User Data Product.

Both products hold retrievals on the ISEA 4H9 discrete global grid.  The
file contains only the grid points inside the MIRAS swath (roughly
1000 km wide), stored as one-dimensional arrays indexed by a grid-point
dimension, with ``Latitude`` and ``Longitude`` giving each point's
position.  There is no regular lat/lon grid, so subsets are selected by
masking on the coordinate variables rather than slicing.

This is example code from the book
`Earth Observation in Practice <https://tinyurl.com/43e26by6>`_.

Author: Edward Hartnett
Date: 2026-10-02
"""

from pathlib import Path

import netCDF4
import numpy as np
import xarray as xr

#: Names used for the geolocation coordinate variables.
LAT_NAMES = ("Latitude", "latitude", "lat")
LON_NAMES = ("Longitude", "longitude", "lon")

#: Primary science variables, in the order they are tried when
#: ``--variable`` is not given.  Covers both the soil moisture product
#: (``MIR_SMUDP2``) and the ocean salinity product (``MIR_OSUDP2``).
DATA_VARIABLES = (
    "Soil_Moisture",
    "SSS_corr",
    "SSS_uncorr",
    "Sea_Surface_Salinity",
    "SSS",
)

Bounds = tuple[float, float, float, float]  # west, south, east, north


def _find_name(ds: netCDF4.Dataset, candidates: tuple[str, ...]) -> str:
    """Return the first *candidates* entry present in ``ds.variables``.

    Raises ``ValueError`` listing the variables found when none match.
    """
    for name in candidates:
        if name in ds.variables:
            return name
    names = ", ".join(sorted(ds.variables))
    raise ValueError(
        f"none of {candidates} found in file; variables present: {names}"
    )


def _masked(var: netCDF4.Variable) -> np.ndarray:
    """Read a netCDF variable as float64 with fill values as NaN."""
    return np.ma.filled(var[:].astype("float64"), np.nan)


def list_variables(path: Path) -> str:
    """Return a printable table of the variables in *path*."""
    lines = []
    with netCDF4.Dataset(path) as ds:
        lines.append(f"dimensions: {', '.join(f'{k}={v.size}' for k, v in ds.dimensions.items())}")
        for name, var in ds.variables.items():
            dims = ",".join(var.dimensions) or "-"
            long_name = getattr(var, "long_name", "")
            units = getattr(var, "units", "")
            lines.append(f"{name} [{dims}] {var.dtype}  {long_name} {units}".rstrip())
    return "\n".join(lines)


def load_grid_point(
    path: Path,
    bounds: Bounds | None = None,
    variable: str | None = None,
) -> xr.DataArray:
    """Load a Level-2 science variable as a scattered ``DataArray``.

    The result is a 1-D array over grid points with ``lat`` and ``lon``
    coordinates.  When *bounds* is given, only points inside the
    ``(west, south, east, north)`` box are kept.

    Parameters
    ----------
    path : Path
        Local ``*MIR_SMUDP2*.nc`` or ``*MIR_OSUDP2*.nc`` file.
    bounds : tuple of float or None, optional
        ``(west, south, east, north)`` in degrees.  ``None`` keeps the
        whole swath.
    variable : str or None, optional
        Science variable to read.  Defaults to the first of
        ``Soil_Moisture``, ``SSS_corr``, ``SSS_uncorr``,
        ``Sea_Surface_Salinity``, ``SSS`` present in the file.

    Returns
    -------
    xarray.DataArray
        The variable with ``lat``/``lon`` coordinates and ``long_name`` /
        ``units`` attributes, plus ``title`` and ``time_coverage_start``
        global attributes when the file carries them.
    """
    with netCDF4.Dataset(path) as ds:
        lat_name = _find_name(ds, LAT_NAMES)
        lon_name = _find_name(ds, LON_NAMES)
        if variable is None:
            variable = _find_name(ds, DATA_VARIABLES)
        var = ds.variables[variable]

        lat = _masked(ds.variables[lat_name])
        lon = _masked(ds.variables[lon_name])
        data = _masked(var)

        if bounds is not None:
            west, south, east, north = bounds
            inside = (
                (lat >= south) & (lat <= north)
                & (lon >= west) & (lon <= east)
            )
            lat, lon, data = lat[inside], lon[inside], data[inside]

        attrs = {
            "long_name": getattr(var, "long_name", variable),
            "units": getattr(var, "units", ""),
        }
        for attr in ("title", "time_coverage_start", "time_coverage_end",
                     "platform", "institution"):
            if attr in ds.ncattrs():
                attrs[attr] = ds.getncattr(attr)

    return xr.DataArray(
        data,
        dims=("grid_point",),
        coords={"lat": ("grid_point", lat), "lon": ("grid_point", lon)},
        name=variable,
        attrs=attrs,
    )
