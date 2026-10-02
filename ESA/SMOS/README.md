# ESA SMOS Level-2 Example

A standalone Python example that opens an ESA SMOS Level-2 netCDF
product, reads a science variable on the ISEA 4H9 grid-point grid, and
plots it on a map and as a histogram. It follows the same layout as
`NASA/NPOS/VIIRS/` and uses the same tools: `netCDF4`, `xarray`,
`numpy`, `matplotlib`, and `cartopy`.

## The Data

SMOS carries MIRAS, an L-band interferometric radiometer. The Level-2
User Data Products are:

| Product | Contents |
|---|---|
| `MIR_SMUDP2` | Soil moisture and vegetation optical thickness over land |
| `MIR_OSUDP2` | Sea surface salinity over ocean |

Each product is a single satellite pass: retrievals for the grid points
inside the roughly 1000 km MIRAS swath. Products come in two formats:
native Earth Explorer format (`.HDR` plus `.DBL`) and netCDF (`*.nc`).
This example reads the netCDF versions.

The netCDF files are not regularly gridded. Data are one-dimensional
arrays over a grid-point dimension, with `Latitude`, `Longitude`, and
`Grid_Point_ID` giving each point's position on the ISEA 4H9 discrete
global grid. Subsetting is done by masking on the coordinate variables.

Key variables in a `MIR_SMUDP2` file:

| Variable | Meaning |
|---|---|
| `Soil_Moisture` | Retrieved soil moisture, m³/m³ |
| `Soil_Moisture_DQX` | Data quality index for the retrieval |
| `Optical_Thickness_Nadir` | Vegetation optical thickness |
| `Surface_Temperature` | Surface temperature used in the retrieval |

`MIR_OSUDP2` files carry the salinity retrieval as `SSS_corr` (and
related variables). Use `--list` to print every variable in a file and
`--variable` to plot a different one, for example
`--variable Soil_Moisture_DQX` to inspect retrieval quality.

Download requires a free ESA EO Sign In:

- SMOS Online Dissemination Service:
  <https://earth.esa.int/eogateway/missions/smos/data>
- Earth Online SMOS data samples:
  <https://earth.esa.int/eogateway/missions/smos/data-samples>

Level-3/4 products in NetCDF-4 are at CATDS:
<https://www.catds.fr/>

Sample files are **not** bundled with this repository. Put a downloaded
`.nc` file under `data/` or pass any path.

## Setup

Requires Python >= 3.10.

```bash
python3 -m venv .venv
.venv/bin/pip install -r ESA/SMOS/requirements.txt
```

## Running the Example

Run from the `ESA/SMOS/` directory.

Plot soil moisture from a `MIR_SMUDP2` pass:

```bash
python -m smos_example data/SM_OPER_MIR_SMUDP2_20230616T063729_20230616T073042_700_001_1.nc
```

Plot salinity from a `MIR_OSUDP2` pass:

```bash
python -m smos_example data/SM_OPER_MIR_OSUDP2_20230616T063729_20230616T073042_700_001_1.nc
```

Restrict to a box (west south east north):

```bash
python -m smos_example data/SM_OPER_MIR_SMUDP2_*.nc --bbox -10 35 5 45
```

See what is in a file:

```bash
python -m smos_example data/SM_OPER_MIR_SMUDP2_*.nc --list
```

Options:

| Flag | Meaning |
|---|---|
| `FILE` | Local SMOS L2 netCDF file (required) |
| `--variable NAME` | Science variable to plot (default: `Soil_Moisture` or `SSS`) |
| `--list` | Print the variables in `FILE` and exit |
| `--bbox W S E N` | Lon/lat box in degrees (default: whole swath) |
| `--output-dir` | Where to write PNGs. Default `output/` |
| `--show` | Also display the figures |

The program prints the number of valid grid points and the value range,
then writes `<variable>_map.png` and `<variable>_histogram.png`.

## Package Layout

```
ESA/SMOS/
├── smos_example/
│   ├── __init__.py
│   ├── __main__.py   # python -m entry point
│   ├── cli.py        # argument parsing and main()
│   ├── reader.py     # ISEA 4H9 grid-point reading, bbox masking
│   └── plots.py      # cartopy scatter map and histogram
├── requirements.txt
└── README.md
```

## How the Reader Works

1. Open the file with `netCDF4` and find the geolocation variables
   (`Latitude`/`Longitude`) and the science variable.
2. Read the one-dimensional arrays over the grid-point dimension;
   `netCDF4` applies `_FillValue` masking.
3. When `--bbox` is given, keep only points inside the box.
4. Return an `xarray.DataArray` with `lat`/`lon` coordinates, ready to
   scatter-plot or merge with other data on the ISEA grid.

## References

- SMOS Online Dissemination Service: <https://earth.esa.int/eogateway/missions/smos/data>
- Earth Online SMOS data samples: <https://earth.esa.int/eogateway/missions/smos/data-samples>
- CATDS Level-3/4 products: <https://www.catds.fr/>
- Book article: `~/Earth_from_Space/ESA/SMOS/smos_mission.md`
