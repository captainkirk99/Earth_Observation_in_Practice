"""Download NOAA gridded VIIRS LST files from the NOAA JPSS AWS Open Data buckets.

Uses ``boto3`` with anonymous (unsigned) requests against the public
``noaa-nesdis-n20-pds`` and ``noaa-nesdis-n21-pds`` buckets.  No AWS or
Earthdata credentials are required.  Files are laid out as::

    GRIDDED_VIIRS_LST_D/YYYY/MM/DD/GRIDDED-VIIRS-LST-D_v1r1_n20_sYYYYMMDD_eYYYYMMDD_c....nc

Downloads are skipped when the file is already present in ``data/``.

This is example code from the book
`Earth Observation in Practice <https://tinyurl.com/43e26by6>`_.

Author: Edward Hartnett
Date: 2026-09-18
"""

from datetime import date, datetime
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config

from .reader import DATA_DIR

#: Satellite name to NOAA JPSS AWS bucket.
SATELLITE_BUCKET = {
    "noaa-20": "noaa-nesdis-n20-pds",
    "noaa-21": "noaa-nesdis-n21-pds",
    "n20": "noaa-nesdis-n20-pds",
    "n21": "noaa-nesdis-n21-pds",
}

#: Product prefix for daytime (D) and nighttime (N) composites.
PRODUCT_PREFIX = {
    "day": "GRIDDED_VIIRS_LST_D",
    "night": "GRIDDED_VIIRS_LST_N",
}


def _s3_client():
    """Return a boto3 S3 client configured for anonymous access."""
    return boto3.client("s3", config=Config(signature_version=UNSIGNED))


def parse_date(date_str: str) -> date:
    """Parse ``YYYY-MM-DD`` into a ``date``."""
    return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()


def resolve_bucket(satellite: str) -> str:
    """Return the NOAA AWS bucket name for a satellite name such as ``NOAA-20``.

    Raises ``ValueError`` for an unknown satellite.
    """
    key = satellite.strip().lower()
    if key not in SATELLITE_BUCKET:
        raise ValueError(
            f"unknown satellite {satellite!r}; expected one of "
            f"{sorted(set(SATELLITE_BUCKET))}"
        )
    return SATELLITE_BUCKET[key]


def list_keys(bucket: str, day: date, period: str = "day") -> list[str]:
    """List gridded LST object keys for one calendar day.

    Raises
    ------
    FileNotFoundError
        If nothing is found under the day's prefix.
    """
    if period not in PRODUCT_PREFIX:
        raise ValueError(f"period must be 'day' or 'night', got {period!r}")
    prefix = f"{PRODUCT_PREFIX[period]}/{day:%Y/%m/%d}/"
    client = _s3_client()
    keys = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".nc"):
                keys.append(obj["Key"])
    if not keys:
        raise FileNotFoundError(f"no files found at s3://{bucket}/{prefix}")
    return sorted(keys)


def fetch_file(bucket: str, key: str, dest_dir: Path = DATA_DIR) -> Path:
    """Download one object unless it is already cached in *dest_dir*."""
    dest_dir = Path(dest_dir)
    local_path = dest_dir / key.rsplit("/", 1)[-1]
    if local_path.exists():
        print(f"Using cached file {local_path}")
        return local_path
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading s3://{bucket}/{key} to {dest_dir}/ ...")
    _s3_client().download_file(bucket, key, str(local_path))
    return local_path


def fetch_for_date(
    satellite: str,
    date_str: str,
    period: str = "day",
    dest_dir: Path = DATA_DIR,
) -> Path:
    """Fetch the gridded VIIRS LST file for one satellite and date.

    When more than one file exists for the day (reprocessing), the most
    recently created one (last in sorted order) is used.
    """
    bucket = resolve_bucket(satellite)
    keys = list_keys(bucket, parse_date(date_str), period)
    key = keys[-1]
    print(f"Selected {key.rsplit('/', 1)[-1]}")
    return fetch_file(bucket, key, dest_dir)
