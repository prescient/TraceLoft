"""Inspect Biber et al.'s downloaded supplementary ZIP without extracting it.

Usage: python research/ball_physics/audit_bounce_data.py PATH_TO_ZIP
Writes a deterministic JSON inventory to stdout. No downloads, fitting, or app imports.
"""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile


SOURCE_URL = (
    "https://media.springernature.com/original/springer-static/esm/"
    "art%3A10.1007%2Fs12283-023-00442-4/MediaObjects/"
    "12283_2023_442_MOESM2_ESM.zip"
)
EXPECTED_SHA256 = "7cb5710d8673857ffa544b720aaf0eea16040d1ff9194b4652abfd02aabe421c"
COLUMNS = ["vx_in", "vy_in", "omega_in", "vx_out", "vy_out", "omega_out"]


def inspect(path):
    raw_zip = path.read_bytes()
    digest = hashlib.sha256(raw_zip).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError("ZIP differs from the inspected source revision; review provenance first")
    report = {
        "source_url": SOURCE_URL,
        "article_doi": "10.1007/s12283-023-00442-4",
        "zip_sha256": digest,
        "columns": COLUMNS,
        "linear_velocity_unit": "ball_radii_per_second",
        "angular_velocity_unit": "radians_per_second_anticlockwise_positive",
        "group_ids_provided": False,
        "campaigns": {},
    }
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        for campaign, expected_count in [("A", 330), ("B", 693)]:
            member = f"ESM_2/data_campaign{campaign}.csv"
            raw = archive.read(member)
            rows = list(csv.reader(io.StringIO(raw.decode("utf-8"))))
            if len(rows) != expected_count or any(len(row) != 6 for row in rows):
                raise ValueError(f"Unexpected dimensions in {member}")
            values = [tuple(float(value) for value in row) for row in rows]
            if not all(math.isfinite(value) for row in values for value in row):
                raise ValueError(f"Nonfinite value in {member}")
            report["campaigns"][campaign] = {
                "member": member,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "rows": len(values),
                "exact_duplicate_rows": len(values) - len(set(values)),
                "inbound_y_nonnegative": sum(row[1] >= 0 for row in values),
                "outbound_y_nonpositive": sum(row[4] <= 0 for row in values),
                "horizontal_velocity_sign_reversals": sum(row[0] * row[3] < 0 for row in values),
                "contact_slip_sign_reversals": sum(
                    (row[0] + row[2]) * (row[3] + row[5]) < 0 for row in values
                ),
                "ranges": {
                    column: {
                        "min": min(row[i] for row in values),
                        "max": max(row[i] for row in values),
                    }
                    for i, column in enumerate(COLUMNS)
                },
            }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path)
    args = parser.parse_args()
    try:
        report = inspect(args.zip_path)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"Audit failed: {exc}\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
