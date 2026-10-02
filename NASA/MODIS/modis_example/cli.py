"""Command-line interface: describe, read, and plot a MODIS HDF4 file.

Usage::

    python -m modis_example [FILE] [--var NAME] [--index N] [--stride N]
                            [--list] [--output-dir output] [--show]

``FILE`` is a MODIS HDF4 file.  If it is omitted, the first ``*.hdf``
file in ``~/Downloads/Earth_from_Space/NASA/MODIS/`` is used.  The
program prints the file's variables, reads one field, and writes a map
(``<var>_map.png``) and an array-space image (``<var>_array.png``).

This is example code from the book
`Earth Observation in Practice <https://tinyurl.com/43e26by6>`_.

Author: Edward Hartnett
Date: 2026-10-02
"""

import argparse
from pathlib import Path

from . import plots, reader

#: Where the book keeps its sample data files.
DEFAULT_DATA_DIR = Path.home() / "Downloads" / "Earth_from_Space" / "NASA" / "MODIS"


def find_default_file() -> Path:
    """Return the first ``*.hdf`` file in :data:`DEFAULT_DATA_DIR`."""
    files = sorted(DEFAULT_DATA_DIR.glob("*.hdf"))
    if not files:
        raise FileNotFoundError(f"no .hdf files in {DEFAULT_DATA_DIR}")
    return files[0]


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, read the requested field, and write the plots.

    ``argv`` defaults to ``sys.argv[1:]``.  Returns a process exit code.
    """
    parser = argparse.ArgumentParser(
        prog="modis_example",
        description="Read and plot a MODIS HDF4 file through the netCDF API.",
    )
    parser.add_argument("file", nargs="?", type=Path, default=None,
                        help=f"MODIS .hdf file (default: first .hdf in {DEFAULT_DATA_DIR})")
    parser.add_argument("--var", default=None,
                        help="variable (SDS) to plot (default: first 2-D data field)")
    parser.add_argument("--index", type=int, default=0,
                        help="index into the leading dimension of a 3-D field (default: 0)")
    parser.add_argument("--stride", type=int, default=1,
                        help="plot every Nth row and column (default: 1)")
    parser.add_argument("--list", action="store_true",
                        help="only list the file's variables")
    parser.add_argument("--output-dir", type=Path, default=Path("output"),
                        help="directory for output PNGs (default: output/)")
    parser.add_argument("--show", action="store_true",
                        help="also display the figures interactively")
    args = parser.parse_args(argv)

    try:
        path = args.file if args.file is not None else find_default_file()
    except FileNotFoundError as exc:
        parser.exit(1, f"{parser.prog}: error: {exc}\n")

    print(reader.describe(path))
    if args.list:
        return 0

    field = reader.load_field(path, args.var, args.index, args.stride)
    valid = field.data.compressed()
    print(f"\n{field.name}: {field.long_name}")
    print(f"  {valid.size} of {field.data.size} values valid", end="")
    if valid.size:
        print(f"; min {valid.min():.3f}, max {valid.max():.3f}, "
              f"mean {valid.mean():.3f} {field.units}", end="")
    print()

    out = args.output_dir
    print(f"Wrote {plots.plot_array(field, out / f'{field.name}_array.png', args.show)}")
    if field.lat is not None:
        print(f"Wrote {plots.plot_map(field, out / f'{field.name}_map.png', args.show)}")
    else:
        print("No geolocation found; map not written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
