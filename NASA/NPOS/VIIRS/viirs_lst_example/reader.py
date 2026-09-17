"""Read NOAA gridded VIIRS land surface temperature (LST) files.

The ``GRIDDED_VIIRS_LST_D`` / ``GRIDDED_VIIRS_LST_N`` products are daily
global composites of NOAA-20 or NOAA-21 VIIRS LST on a 21600 x 43200
grid.  The file is CF-1.5 NetCDF-4 but carries **no** latitude or
longitude coordinate variables.  The grid is a global sinusoidal
projection (``projection_type = "sinusoidal"``) at 1/120 degree
(about 1 km) sampling.  Row 0 is the north pole (90 N); column 0 is
x = -180 degrees, where ``x = lon * cos(lat)``.

This module maps a lat/lon bounding box onto that grid and returns the
subset as an ``xarray.DataArray`` on a regular lat/lon grid.
"""

from pathlib import Path

import netCDF4
import numpy as np
import xarray as xr

#: Default download directory (relative to the current working directory).
DATA_DIR = Path("data")

#: Grid cells per degree in both row and column direction.
CELLS_PER_DEGREE = 120

#: Full grid shape: (rows, columns).
GRID_SHAPE = (180 * CELLS_PER_DEGREE, 360 * CELLS_PER_DEGREE)

Bounds = tuple[float, float, float, float]  # west, south, east, north


def _validate_bounds(bounds: Bounds) -> Bounds:
    west, south, east, north = bounds
    if not (-180.0 <= west < east <= 180.0):
        raise ValueError(f"longitude bounds out of order or range: {bounds}")
    if not (-90.0 <= south < north <= 90.0):
        raise ValueError(f"latitude bounds out of order or range: {bounds}")
    return west, south, east, north


def lonlat_grid(bounds: Bounds) -> tuple[np.ndarray, np.ndarray]:
    """Return 1-D ``lat`` (north to south) and ``lon`` arrays at grid spacing.

    Cell centers are placed at half-cell offsets so they line up with the
    sinusoidal grid rows.
    """
    west, south, east, north = _validate_bounds(bounds)
    step = 1.0 / CELLS_PER_DEGREE
    lat = np.arange(north - step / 2, south, -step)
    lon = np.arange(west + step / 2, east, step)
    return lat, lon


def sinusoidal_indices(
    lat: np.ndarray, lon: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Convert 2-D latitude/longitude arrays to (row, column) grid indices.

    Parameters
    ----------
    lat, lon : numpy.ndarray
        Arrays of equal shape, in degrees.

    Returns
    -------
    tuple of numpy.ndarray
        Integer ``(rows, cols)`` into the 21600 x 43200 grid.
    """
    x = lon * np.cos(np.deg2rad(lat))
    rows = np.floor((90.0 - lat) * CELLS_PER_DEGREE).astype(int)
    cols = np.floor((x + 180.0) * CELLS_PER_DEGREE).astype(int)
    rows = np.clip(rows, 0, GRID_SHAPE[0] - 1)
    cols = np.clip(cols, 0, GRID_SHAPE[1] - 1)
    return rows, cols


def load_lst(
    path: Path, bounds: Bounds, variable: str | None = None
) -> xr.DataArray:
    """Load an LST subset for *bounds* as a lat/lon ``DataArray`` in kelvin.

    Only the block of the file covering the requested box is read, so the
    global 294 MB file is never fully loaded.  Pixels flagged bad by
    ``DQF`` (``1``) or stored as ``_FillValue`` are returned as NaN.

    Parameters
    ----------
    path : Path
        Local ``GRIDDED-VIIRS-LST-*.nc`` file.
    bounds : tuple of float
        ``(west, south, east, north)`` in degrees.
    variable : str or None, optional
        ``LST_Day`` or ``LST_Night``.  Defaults to whichever is present.

    Returns
    -------
    xarray.DataArray
        LST in kelvin with ``lat`` and ``lon`` coordinates, plus the file's
        ``platform``, ``time_coverage_start`` and ``time_coverage_end``
        global attributes.
    """
    lat, lon = lonlat_grid(bounds)
    lon2d, lat2d = np.meshgrid(lon, lat)
    rows, cols = sinusoidal_indices(lat2d, lon2d)

    with netCDF4.Dataset(path) as ds:
        if variable is None:
            variable = "LST_Day" if "LST_Day" in ds.variables else "LST_Night"
        var = ds.variables[variable]
        r0, r1 = rows.min(), rows.max() + 1
        c0, c1 = cols.min(), cols.max() + 1
        block = var[r0:r1, c0:c1]
        dqf_block = ds.variables["DQF"][r0:r1, c0:c1]
        attrs = {
            "long_name": var.long_name,
            "units": var.units,
            "platform": ds.platform,
            "instrument": ds.instrument,
            "time_coverage_start": ds.time_coverage_start,
            "time_coverage_end": ds.time_coverage_end,
        }

    lst = np.ma.filled(block[rows - r0, cols - c0].astype("float64"), np.nan)
    dqf = np.ma.filled(dqf_block[rows - r0, cols - c0], 1)
    lst[dqf != 0] = np.nan

    return xr.DataArray(
        lst,
        dims=("lat", "lon"),
        coords={"lat": lat, "lon": lon},
        name=variable,
        attrs=attrs,
    )
