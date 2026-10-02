"""Read MODIS HDF4 (HDF-EOS2) science products through the netCDF API.

netCDF-C built with HDF4 support opens MODIS ``.hdf`` files with
``nc_open()``, and ``netCDF4.Dataset`` built against that library does
the same.  Each HDF4 Scientific Data Set (SDS) appears as a netCDF
variable.  The HDF-EOS2 structure (swath or grid, dimension maps, map
projection) is not interpreted by netCDF; it is stored as ODL text in
the ``StructMetadata.0`` global attribute.  This module parses the
parts of that text needed to put latitude and longitude on the data:

* **Swath** products (Level 2, e.g. MOD29, MOD11_L2, MOD04_L2) carry
  ``Latitude`` and ``Longitude`` SDSs, usually at 5 km while the data
  are at 1 km.  The ``DimensionMap`` entries give the offset and
  increment between the two, and the geolocation is interpolated to the
  data resolution.
* **Grid** products (Level 2G/3, e.g. MOD09GA, MOD11A1, MOD13A2) carry
  no coordinates at all.  The grid corners and projection
  (``GCTP_SNSOID`` sinusoidal tiles or ``GCTP_GEO`` climate modeling
  grids) are read from the ODL and lat/lon are computed per pixel.

MODIS stores packed integers with the HDF4 convention
``value = scale_factor * (stored - add_offset)``, not the CF convention
``value = stored * scale_factor + add_offset``.  The two agree only when
``add_offset`` is 0, so automatic CF scaling is turned off and the HDF4
formula is applied here.

This is example code from the book
`Earth Observation in Practice <https://tinyurl.com/43e26by6>`_.

Author: Edward Hartnett
Date: 2026-10-02
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import netCDF4
import numpy as np

#: Sphere radius (m) used by the MODIS sinusoidal grid.
SINUSOIDAL_RADIUS = 6371007.181

#: Variable names treated as geolocation, never as data.
GEOLOCATION_NAMES = ("Latitude", "Longitude")


@dataclass
class ModisField:
    """One MODIS data field, scaled to physical units, with geolocation."""

    name: str
    data: np.ma.MaskedArray
    attrs: dict = field(default_factory=dict)
    lat: np.ndarray | None = None
    lon: np.ndarray | None = None
    granule: str = ""
    long_name: str = ""
    units: str = ""


def short_dim_name(name: str) -> str:
    """Strip the ``:SwathOrGridName`` suffix netCDF-C adds to HDF-EOS dimensions."""
    return name.split(":", 1)[0]


def odl_value(text: str, key: str) -> str | None:
    """Return the first ``key=value`` value found in ODL ``text``, or ``None``."""
    match = re.search(rf"\b{re.escape(key)}=(.+)", text)
    return match.group(1).strip().strip('"') if match else None


def odl_tuple(text: str, key: str) -> tuple[float, ...] | None:
    """Return a parenthesized numeric ODL value such as ``(x,y)`` as floats."""
    value = odl_value(text, key)
    if value is None:
        return None
    return tuple(float(v) for v in value.strip("()").split(","))


def granule_attr(ds: netCDF4.Dataset, key: str) -> str:
    """Read one ``VALUE`` from the ``CoreMetadata.0`` or ``ArchiveMetadata.0`` ODL."""
    for att in ("CoreMetadata.0", "ArchiveMetadata.0"):
        if att not in ds.ncattrs():
            continue
        match = re.search(
            rf"OBJECT\s*=\s*{key}\b.*?VALUE\s*=\s*(.+?)\n", ds.getncattr(att), re.S
        )
        if match:
            return match.group(1).strip().strip('"')
    return ""


def describe(path: Path) -> str:
    """Return a printable summary of the file: format, variables, shapes, types."""
    lines = []
    with netCDF4.Dataset(path) as ds:
        lines.append(f"{Path(path).name}")
        lines.append(f"  disk format: {ds.disk_format}")
        product = granule_attr(ds, "LONGNAME") or granule_attr(ds, "SHORTNAME")
        lines.append(f"  product:     {product}")
        lines.append(f"  start:       {granule_attr(ds, 'RANGEBEGINNINGDATE')} "
                     f"{granule_attr(ds, 'RANGEBEGINNINGTIME')}")
        for name, var in ds.variables.items():
            dims = " x ".join(f"{short_dim_name(d)}={n}" for d, n in
                              zip(var.dimensions, var.shape))
            lines.append(f"  {name:<40} {str(var.dtype):<8} {dims}")
    return "\n".join(lines)


def default_variable(ds: netCDF4.Dataset) -> str:
    """Return the first variable with two or more dimensions that is not geolocation."""
    for name, var in ds.variables.items():
        if var.ndim >= 2 and name not in GEOLOCATION_NAMES:
            return name
    raise ValueError("no 2-D data variable found")


def unpack(var: netCDF4.Variable, raw: np.ma.MaskedArray) -> np.ma.MaskedArray:
    """Apply the HDF4 scale/offset convention and mask values outside ``valid_range``.

    ``raw`` must have been read with automatic scaling turned off, so it
    still holds stored integers (``_FillValue`` already masked).
    """
    attrs = var.ncattrs()
    data = np.ma.masked_invalid(raw.astype("float64"))
    if "valid_range" in attrs:
        lo, hi = var.valid_range
        data = np.ma.masked_outside(data, lo, hi)
    scale = float(var.scale_factor) if "scale_factor" in attrs else 1.0
    offset = float(var.add_offset) if "add_offset" in attrs else 0.0
    return scale * (data - offset)


def _interp_axis(values: np.ndarray, n_out: int, offset: float, increment: float,
                 axis: int) -> np.ndarray:
    """Linearly interpolate ``values`` along ``axis`` from geolocation to data index.

    Geolocation sample ``k`` lies at data index ``offset + k * increment``.
    Points beyond the first and last sample are held constant.
    """
    src = offset + increment * np.arange(values.shape[axis])
    dst = np.arange(n_out)
    return np.apply_along_axis(lambda v: np.interp(dst, src, v), axis, values)


def swath_geolocation(ds: netCDF4.Dataset, var: netCDF4.Variable,
                      shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray] | None:
    """Return 2-D lat/lon at data resolution for a swath field, or ``None``."""
    if not all(n in ds.variables for n in GEOLOCATION_NAMES):
        return None
    lat = np.ma.filled(ds.variables["Latitude"][:].astype("float64"), np.nan)
    lon = np.ma.filled(ds.variables["Longitude"][:].astype("float64"), np.nan)
    if lat.shape == shape:
        return lat, lon

    struct = ds.getncattr("StructMetadata.0")
    geo_dims = [short_dim_name(d) for d in ds.variables["Latitude"].dimensions]
    data_dims = [short_dim_name(d) for d in var.dimensions[-2:]]

    # Unwrap longitude so swaths that cross 180 degrees interpolate smoothly.
    lon = np.rad2deg(np.unwrap(np.unwrap(np.deg2rad(lon), axis=1), axis=0))
    for axis, (gdim, ddim) in enumerate(zip(geo_dims, data_dims)):
        block = re.search(
            rf'GeoDimension="{gdim}"\s+DataDimension="{ddim}"\s+'
            rf"Offset=(-?\d+)\s+Increment=(\d+)", struct)
        if block is None:
            return None
        offset, increment = float(block.group(1)), float(block.group(2))
        lat = _interp_axis(lat, shape[axis], offset, increment, axis)
        lon = _interp_axis(lon, shape[axis], offset, increment, axis)
    lon = (lon + 180.0) % 360.0 - 180.0
    return lat, lon


def grid_geolocation(ds: netCDF4.Dataset,
                     shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray] | None:
    """Return 2-D lat/lon for a sinusoidal or geographic HDF-EOS grid, or ``None``."""
    struct = ds.getncattr("StructMetadata.0")
    if "GridStructure" not in struct or "GROUP=GRID_1" not in struct:
        return None
    upper_left = odl_tuple(struct, "UpperLeftPointMtrs")
    lower_right = odl_tuple(struct, "LowerRightMtrs")
    projection = odl_value(struct, "Projection")
    if upper_left is None or lower_right is None:
        return None
    nrows, ncols = shape
    dx = (lower_right[0] - upper_left[0]) / ncols
    dy = (lower_right[1] - upper_left[1]) / nrows
    x = upper_left[0] + dx * (np.arange(ncols) + 0.5)
    y = upper_left[1] + dy * (np.arange(nrows) + 0.5)
    xx, yy = np.meshgrid(x, y)

    if projection == "GCTP_SNSOID":
        lat = np.rad2deg(yy / SINUSOIDAL_RADIUS)
        with np.errstate(divide="ignore", invalid="ignore"):
            lon = np.rad2deg(xx / (SINUSOIDAL_RADIUS * np.cos(np.deg2rad(lat))))
        lon[np.abs(lon) > 180.0] = np.nan
        return lat, lon
    if projection == "GCTP_GEO":
        # Corners are packed DMS (DDDMMMSSS.SS); whole-degree corners divide by 1e6.
        return yy / 1.0e6, xx / 1.0e6
    return None


def load_field(path: Path, name: str | None = None, index: int = 0,
               stride: int = 1) -> ModisField:
    """Read one MODIS field, unpack it, and attach latitude and longitude.

    Parameters
    ----------
    path : Path
        MODIS HDF4 file, e.g. ``MOD11_L2.A2026258.1850.061.*.hdf``.
    name : str or None
        Variable (SDS) name.  Defaults to the first non-geolocation 2-D field.
    index : int
        Index into the leading dimension of a 3-D field (for example the
        band dimension of ``EV_1KM_RefSB`` in MOD021KM).
    stride : int
        Keep every ``stride``-th row and column, to make plotting faster.
    """
    with netCDF4.Dataset(path) as ds:
        ds.set_auto_scale(False)
        name = name or default_variable(ds)
        var = ds.variables[name]
        raw = var[index] if var.ndim == 3 else var[:]
        if raw.ndim != 2:
            raise ValueError(f"{name} has {var.ndim} dimensions; need 2 or 3")
        data = unpack(var, np.ma.asarray(raw))
        geo = swath_geolocation(ds, var, data.shape) or grid_geolocation(ds, data.shape)
        attrs = {a: var.getncattr(a) for a in var.ncattrs()}
        granule = granule_attr(ds, "LOCALGRANULEID") or Path(path).name

    lat, lon = geo if geo is not None else (None, None)
    s = slice(None, None, stride)
    return ModisField(
        name=name,
        data=data[s, s],
        attrs=attrs,
        lat=None if lat is None else lat[s, s],
        lon=None if lon is None else lon[s, s],
        granule=granule,
        long_name=str(attrs.get("long_name", name)),
        units=str(attrs.get("units", "")),
    )
