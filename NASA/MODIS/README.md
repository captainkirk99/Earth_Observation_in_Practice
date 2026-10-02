# NASA MODIS HDF4 Example

Python and C examples that open a MODIS HDF4 (HDF-EOS2) science product
through the netCDF API, apply the MODIS packing attributes, and plot one
field. They need a netCDF-C library built with HDF4 support; no HDF4 or
HDF-EOS2 calls appear in the code.

## The Data

MODIS standard products from LP DAAC, LAADS DAAC, and NSIDC are HDF4
files that follow the HDF-EOS2 conventions. When netCDF-C is built with
`--enable-hdf4`, `nc_open()` reads these files directly. Each HDF4
Scientific Data Set (SDS) becomes a netCDF variable, and each SDS
attribute becomes a netCDF attribute.

The book uses this granule:

```
MYD29.A2009152.0000.005.2009153124331.hdf
```

It is the Aqua MODIS Sea Ice Extent 5-Min L2 Swath 1km product
(MYD29, Collection 5) for 00:00 UTC on 1 June 2009. It is 2.7 MB and
can be downloaded without a login from the Unidata netCDF-C test data:

```bash
mkdir -p ~/Downloads/Earth_from_Space/NASA/MODIS
cd ~/Downloads/Earth_from_Space/NASA/MODIS
curl -O https://resources.unidata.ucar.edu/netcdf/sample_data/hdf4/MYD29.A2009152.0000.005.2009153124331.hdf.gz
gunzip MYD29.A2009152.0000.005.2009153124331.hdf.gz
```

Current MYD29 granules (Version 6.1) are at NSIDC:
<https://nsidc.org/data/myd29/versions/61>. Other MODIS products are at
<https://search.earthdata.nasa.gov/> (free Earthdata login).

Variables in the sample:

| Variable | Type | Shape | Meaning |
|---|---|---|---|
| `Latitude` | `float` | 406 x 271 | Latitude every 5th pixel, degrees |
| `Longitude` | `float` | 406 x 271 | Longitude every 5th pixel, degrees |
| `Sea_Ice_by_Reflectance` | `ubyte` | 2030 x 1354 | Classification code |
| `Sea_Ice_by_Reflectance_Pixel_QA` | `ubyte` | 2030 x 1354 | QA code |
| `Ice_Surface_Temperature` | `ushort`, scale 0.01 | 2030 x 1354 | Surface temperature, kelvin |
| `Ice_Surface_Temperature_Pixel_QA` | `ubyte` | 2030 x 1354 | QA code |

Two HDF4 details matter:

- **Packing.** MODIS HDF4 files use `value = scale_factor * (stored - add_offset)`.
  The CF convention used by netCDF-4 is `stored * scale_factor + add_offset`.
  The Python example turns off automatic scaling and applies the HDF4
  formula itself. Values equal to `_FillValue` or outside `valid_range`
  are masked.
- **Geolocation.** The 1 km data fields have no 1 km latitude or
  longitude. The 5 km `Latitude` and `Longitude` fields are linked to
  the data dimensions by a dimension map in the `StructMetadata.0`
  global attribute (offset 2, increment 5 in this file). The reader
  parses that map and interpolates to the full grid. For HDF-EOS2 grid
  products (for example MOD11A1 or MOD13A2 tiles), it computes latitude
  and longitude from the grid corners and projection in
  `StructMetadata.0`.

## Requirements

- netCDF-C built with HDF4 (`nc-config --has-hdf4` prints `yes`). The
  examples assume it is installed in `/usr/local/netcdf-c_hdf4`.
- HDF4 4.x (tested with 4.4.0) and HDF5.
- Python >= 3.10.

The `netCDF4` Python wheels on PyPI bundle their own netCDF-C without
HDF4. Build the Python package from source against the HDF4-enabled
library:

```bash
cd NASA/MODIS
python3 -m venv .venv
.venv/bin/pip install numpy matplotlib cartopy cython
PATH=/usr/local/netcdf-c_hdf4/bin:$PATH \
NETCDF4_DIR=/usr/local/netcdf-c_hdf4 \
HDF5_DIR=/usr/local/hdf5-2.1.1 \
    .venv/bin/pip install --no-binary netCDF4 --no-build-isolation --no-cache-dir netCDF4
.venv/bin/python -c "import netCDF4; print(netCDF4.__netcdf4libversion__)"
```

If HDF5 is installed elsewhere, set `HDF5_DIR` (or `HDF5_INCDIR` and
`HDF5_LIBDIR`) to match. If `libnetcdf` is not on the runtime library
path, add `LD_LIBRARY_PATH=/usr/local/netcdf-c_hdf4/lib`.

## Python Example

```bash
cd NASA/MODIS
.venv/bin/python -m modis_example --list
.venv/bin/python -m modis_example --var Ice_Surface_Temperature
```

With no file argument the program uses the first `.hdf` file in
`~/Downloads/Earth_from_Space/NASA/MODIS/`. Options:

| Option | Meaning |
|---|---|
| `FILE` | MODIS `.hdf` file |
| `--var NAME` | Variable to plot (default: first 2-D data field) |
| `--index N` | Index into the leading dimension of a 3-D field |
| `--stride N` | Plot every Nth row and column |
| `--list` | Only list the variables |
| `--output-dir DIR` | Where to write PNGs (default `output/`) |
| `--show` | Also open the figures in a window |

Output for the sample granule:

```
Ice_Surface_Temperature: Ice Surface Temperature by split-window method
  1019119 of 2748620 values valid; min 278.220, max 299.910, mean 291.058 degree_Kelvin
Wrote output/Ice_Surface_Temperature_array.png
Wrote output/Ice_Surface_Temperature_map.png
```

`Ice_Surface_Temperature_array.png` shows the field in swath
coordinates. `Ice_Surface_Temperature_map.png` places it on a map using
the interpolated geolocation.

Package layout:

| File | Purpose |
|---|---|
| `modis_example/reader.py` | Open the file, unpack a field, build latitude and longitude |
| `modis_example/plots.py` | Array-space image and Cartopy map |
| `modis_example/cli.py` | Command-line interface |

## C Example

```bash
cd NASA/MODIS/c
make
./modis_read ~/Downloads/Earth_from_Space/NASA/MODIS/MYD29.A2009152.0000.005.2009153124331.hdf \
    Ice_Surface_Temperature
```

Set `NC_CONFIG` to use a different netCDF-C installation:
`make NC_CONFIG=/path/to/nc-config`.

Output:

```
  extended format: NC_FORMATX_NC_HDF4
  6 variables, 9 global attributes
...
Variable Ice_Surface_Temperature
  long_name      Ice Surface Temperature by split-window method
  units          degree_Kelvin
  scale_factor   0.01
  add_offset     0
  _FillValue     65535
  valid_range    21000 31300
  1019119 of 2748620 values valid; min 278.220, max 299.910, mean 291.058
```
