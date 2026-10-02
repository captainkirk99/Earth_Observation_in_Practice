"""Command-line interface: plot an ESA SMOS Level-2 product on a map.

Usage::

    python -m smos_example FILE [--variable NAME] [--bbox W S E N]
                            [--output-dir output] [--show]
    python -m smos_example FILE --list

``FILE`` is a local SMOS Level-2 netCDF product (``*MIR_SMUDP2*.nc``
soil moisture or ``*MIR_OSUDP2*.nc`` sea surface salinity, not bundled
with this repository).  The science variable defaults to soil moisture
or salinity depending on the product; ``--variable`` picks any other
variable in the file and ``--list`` prints what is available.  Two PNGs
are written to the output directory: ``<variable>_map.png`` and
``<variable>_histogram.png``.

This is example code from the book
`Earth Observation in Practice <https://tinyurl.com/43e26by6>`_.

Author: Edward Hartnett
Date: 2026-10-02
"""

import argparse
from pathlib import Path

import numpy as np

from . import plots, reader


def main(argv: list[str] | None = None) -> int:
    """Parse command-line arguments, load the retrieval, and write the plots.

    ``argv`` defaults to ``sys.argv[1:]``.  Returns a process exit code
    (0 on success).
    """
    parser = argparse.ArgumentParser(
        prog="plot-smos-l2",
        description="Plot an ESA SMOS Level-2 netCDF product on a map.",
    )
    parser.add_argument("file", type=Path,
                        help="local SMOS L2 netCDF file (MIR_SMUDP2 or MIR_OSUDP2)")
    parser.add_argument("--variable", metavar="NAME",
                        help="science variable to plot (default: Soil_Moisture or SSS)")
    parser.add_argument("--list", action="store_true",
                        help="list the variables in FILE and exit")
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("W", "S", "E", "N"),
                        default=None,
                        help="lon/lat bounding box in degrees (default: whole swath)")
    parser.add_argument("--output-dir", type=Path, default=Path("output"),
                        help="directory for output PNGs (default: output/)")
    parser.add_argument("--show", action="store_true",
                        help="also display the figures interactively")
    args = parser.parse_args(argv)

    if args.list:
        print(reader.list_variables(args.file))
        return 0

    da = reader.load_grid_point(
        args.file, bounds=tuple(args.bbox) if args.bbox else None,
        variable=args.variable,
    )
    valid = int(np.isfinite(da.values).sum())
    units = da.attrs.get("units", "")
    print(f"{da.name}: {valid} of {da.size} grid points valid; "
          f"range {float(da.min()):.3g}-{float(da.max()):.3g} {units}")

    map_png = plots.plot_map(
        da, out_path=args.output_dir / f"{da.name}_map.png", show=args.show)
    hist_png = plots.plot_histogram(
        da, out_path=args.output_dir / f"{da.name}_histogram.png", show=args.show)
    print(f"Wrote {map_png}")
    print(f"Wrote {hist_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
