# Earth Observation in Practice: Code Examples

This repository holds the public example code for [*Earth Observation in Practice: A Mission-by-Mission Guide to Reading Satellite Data with NetCDF and Python*](https://www.amazon.com/dp/B0HJRZ9F7L), a book by Edward Hartnett.

## What the Examples Cover

Each example reads data from a civil Earth observation mission and produces a plot or summary. They complement the NetCDF techniques covered in [*The NetCDF Developer's Handbook*](https://www.amazon.com/dp/B0H7Q49MPS). The current examples are:

- **CNES / NASA SWOT**: read the Level 2 KaRIn Low Rate Sea Surface Height product and plot sea surface height anomaly.
- **ESA Sentinel-3 OLCI**: read Ocean and Land Colour Instrument data and plot a true-color or band-ratio image.
- **ESA Sentinel-3 SLSTR**: read Sea and Land Surface Temperature Radiometer Level-2 products and print a variable summary.
- **ESA Sentinel-3 SRAL**: read Synthetic Aperture Radar Altimeter Level-2 measurement products and print a variable summary.
- **ESA MetOp-SG GRAS-2**: read a Level-1B radio-occultation product and plot its neutral bending-angle profile.
- **ESA MetOp-SG METimage**: read Level-1B visible radiances and create a true-color swath image.
- **ESA Sentinel-6**: read Poseidon-4 altimetry NetCDF-4 files and print a variable summary.
- **ISRO NISAR**: read simulated NISAR L2 products and plot a parameter map.
- **NASA / NOAA GOES-R ABI**: read Advanced Baseline Imager Cloud and Moisture Imagery NetCDF-4 files and plot on the native geostationary projection.

## Repository Layout

```
.
├── CNES/swot/swot_example/        # SWOT KaRIn SSH example package
├── ESA/Sentinel-3/olci/olci_example/  # Sentinel-3 OLCI example package
├── ESA/Sentinel-3/SLSTR/examples/   # Sentinel-3 SLSTR standalone script
├── ESA/Sentinel-3/SRAL/examples/    # Sentinel-3 SRAL standalone script
├── ESA/MetOp/GRAS-2/examples/       # MetOp-SG GRAS-2 profile script
├── ESA/MetOp/METimage/examples/     # MetOp-SG METimage image script
├── ESA/Sentinel-6/examples/       # Sentinel-6 standalone script
├── ISRO/nisar/nisar_example/        # NISAR example package
└── NASA/GOES/abi/abi_example/       # GOES-R ABI example package
```

Each mission directory contains a `README.md` with exact dependencies, data-source links, and run instructions. Check there before running an example.

## Common Dependencies

Most examples use:

- `netCDF4` or `xarray` for NetCDF-4 files
- `numpy` and `matplotlib` for analysis and plotting
- `cartopy` for map projections
- `earthaccess` or `boto3` for downloading data from NASA Earthdata or AWS Open Data

Create a virtual environment inside the example directory and install its `requirements.txt`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Data

The examples do not bundle satellite data. Each `README.md` points to the public archive where you can download the file used in the book, or shows how to fetch data automatically.

## License

The code is released under the MIT License. See `LICENSE`.
