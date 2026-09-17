"""Command-line interface: plot NOAA gridded VIIRS LST for a lat/lon box.

Usage::

    python -m viirs_lst_example FILE [--bbox W S E N] [--output-dir output] [--show]
    python -m viirs_lst_example --date YYYY-MM-DD [--satellite NOAA-20] [--night] [--bbox W S E N]

``FILE`` is a local ``GRIDDED-VIIRS-LST-*.nc`` file (about 294 MB, not
bundled with this repository).  Alternatively, ``--date`` downloads the
daily composite for that date from the NOAA JPSS AWS Open Data bucket
into ``data/`` (no credentials needed).  The default bounding box covers
the Central Valley of California.  Two PNGs are written to the output
directory: ``lst_map.png`` and ``footprint.png``.
"""

import argparse
from pathlib import Path

from . import fetch, plots, reader

#: Default box: California Central Valley and the Sierra Nevada.
CENTRAL_VALLEY = (-123.0, 34.5, -117.5, 41.0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="plot-viirs-lst",
        description="Plot NOAA gridded VIIRS land surface temperature for a lat/lon box.",
    )
    parser.add_argument("file", nargs="?", type=Path, default=None,
                        help="local GRIDDED-VIIRS-LST .nc file")
    parser.add_argument("--date", metavar="YYYY-MM-DD",
                        help="fetch the daily composite for this UTC date from AWS")
    parser.add_argument("--satellite", default="NOAA-20",
                        help="NOAA-20 or NOAA-21 (default: NOAA-20)")
    parser.add_argument("--night", action="store_true",
                        help="use the nighttime composite (default: daytime)")
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("W", "S", "E", "N"),
                        default=CENTRAL_VALLEY,
                        help="lon/lat bounding box in degrees (default: Central Valley, CA)")
    parser.add_argument("--output-dir", type=Path, default=Path("output"),
                        help="directory for output PNGs (default: output/)")
    parser.add_argument("--show", action="store_true",
                        help="also display the figures interactively")
    args = parser.parse_args(argv)

    if args.date is not None and args.file is not None:
        parser.error("--date and FILE are mutually exclusive")
    if args.date is not None:
        try:
            path = fetch.fetch_for_date(
                args.satellite, args.date, "night" if args.night else "day"
            )
        except (ValueError, FileNotFoundError) as exc:
            parser.exit(1, f"{parser.prog}: error: {exc}\n")
    elif args.file is not None:
        path = args.file
    else:
        parser.error("a FILE path or --date is required")

    lst = reader.load_lst(path, tuple(args.bbox))
    valid = int(lst.notnull().sum())
    print(f"{lst.name}: {valid} of {lst.size} pixels valid; "
          f"range {float(lst.min()):.1f}-{float(lst.max()):.1f} K")

    map_png = plots.plot_lst_map(lst, out_path=args.output_dir / "lst_map.png", show=args.show)
    fp_png = plots.plot_footprint(lst, out_path=args.output_dir / "footprint.png", show=args.show)
    print(f"Wrote {map_png}")
    print(f"Wrote {fp_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
