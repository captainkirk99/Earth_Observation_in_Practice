# NOAA JPSS VIIRS Gridded Land Surface Temperature Example

A standalone Python example that opens a NOAA gridded VIIRS Land Surface
Temperature (LST) NetCDF-4 file, cuts out a latitude/longitude box, and
plots it on a map. It follows the same layout as `NASA/GOES/abi/` and
uses the same tools: `netCDF4`, `xarray`, `numpy`, `matplotlib`,
`cartopy`, and `boto3`.

The default box is the Central Valley of California and the Sierra
Nevada. Daytime LST there separates irrigated fields (cool, high
evapotranspiration) from dry grassland and foothills (hot), which makes
this product a useful layer in water-system training data.

## The Data

NOAA produces `GRIDDED_VIIRS_LST_D` (daytime) and `GRIDDED_VIIRS_LST_N`
(nighttime) daily from NOAA-20 and NOAA-21 VIIRS. Each file is one day
of global LST composited onto a fixed 21600 x 43200 grid at 1/120
degree (about 1 km). Files are about 294 MB and are NetCDF-4 classic
model, CF-1.5.

Variables in a daytime file:

| Variable | Type | Meaning |
|---|---|---|
| `LST_Day` | `int16`, scale 0.005, offset 200 | LST in kelvin |
| `QC_Day` | `int8` | LST algorithm quality bits |
| `DQF` | `int8` | Overall quality: 0 good, 1 bad |
| `View_Angle_Day` | `int8` | View zenith angle, degrees |
| `View_Time_Day` | `int8`, scale 0.1, offset 12 | Local observation hour |

The file has **no latitude or longitude variables**. The global
attribute `projection_type = "sinusoidal"` tells you how to map the
grid. Row `r` is latitude `90 - r/120`. Column `c` is
`x = c/120 - 180` where `x = lon * cos(lat)`. Indexing the array as if
it were a plain lat/lon grid returns fill values over most of the
Earth. See `viirs_lst_example/reader.py` for the conversion.

The files are on the NOAA JPSS AWS Open Data buckets and need no
credentials:

- `s3://noaa-nesdis-n20-pds/GRIDDED_VIIRS_LST_D/YYYY/MM/DD/`
- `s3://noaa-nesdis-n21-pds/GRIDDED_VIIRS_LST_D/YYYY/MM/DD/`

Registry page: <https://registry.opendata.aws/noaa-jpss/>

Product page: <https://www.star.nesdis.noaa.gov/jpss/lst.php>

Sample files are **not** bundled with this repository. Either give a
local path or use `--date` to download one into `data/`.

## Setup

Requires Python >= 3.10.

```bash
python3 -m venv .venv
.venv/bin/pip install -r NASA/NPOS/VIIRS/requirements.txt
```

## Running the Example

Run from the `NASA/NPOS/VIIRS/` directory.

Download and plot the NOAA-20 daytime composite for 15 September 2026:

```bash
python -m viirs_lst_example --date 2026-09-15
```

Use a file you already have:

```bash
python -m viirs_lst_example data/GRIDDED-VIIRS-LST-D_v1r1_n20_s20260915_e20260915_c202609160304370.nc
```

Nighttime LST from NOAA-21 over a different box (west south east north):

```bash
python -m viirs_lst_example --date 2026-09-16 --satellite NOAA-21 --night --bbox -105 30 -95 40
```

Options:

| Flag | Meaning |
|---|---|
| `FILE` | Local `GRIDDED-VIIRS-LST-*.nc` file |
| `--date YYYY-MM-DD` | Fetch that day's composite from AWS instead of using `FILE` |
| `--satellite` | `NOAA-20` (default) or `NOAA-21` |
| `--night` | Use the nighttime product |
| `--bbox W S E N` | Lon/lat box in degrees. Default `-123 34.5 -117.5 41` |
| `--output-dir` | Where to write PNGs. Default `output/` |
| `--show` | Also display the figures |

The program prints the number of valid pixels and the LST range, then
writes `lst_map.png` and `footprint.png`.

## Package Layout

```
NASA/NPOS/VIIRS/
├── viirs_lst_example/
│   ├── __init__.py
│   ├── __main__.py   # python -m entry point
│   ├── cli.py        # argument parsing and main()
│   ├── fetch.py      # anonymous boto3 download from noaa-nesdis-n2x-pds
│   ├── reader.py     # sinusoidal grid indexing, scaling, DQF masking
│   └── plots.py      # cartopy map and footprint plots
├── requirements.txt
└── README.md
```

## How the Reader Works

1. Build 1-D `lat` and `lon` arrays for the box at 1/120 degree spacing.
2. Compute `rows = floor((90 - lat) * 120)` and
   `cols = floor((lon * cos(lat) + 180) * 120)` for every cell.
3. Read only the enclosing block of `LST_Day` and `DQF` from the file,
   so the 294 MB global array is never loaded in full.
4. Let `netCDF4` apply `scale_factor` and `add_offset` and mask
   `_FillValue`; set pixels with `DQF != 0` to NaN.
5. Return an `xarray.DataArray` on the regular lat/lon grid, ready to
   stack with other layers.

## References

- NOAA STAR JPSS Land Surface Temperature: <https://www.star.nesdis.noaa.gov/jpss/lst.php>
- NOAA JPSS on AWS Open Data: <https://registry.opendata.aws/noaa-jpss/>
- JPSS VIIRS LST Algorithm Theoretical Basis Document (ATBD): <https://www.star.nesdis.noaa.gov/jpss/documents/ATBD/ATBD_EPS_Land_LST_v1.1.pdf>
- Book article: `~/Earth_from_Space/NASA/NPOS/VIIRS/netCDF_with_VIIRS_LST.md`
