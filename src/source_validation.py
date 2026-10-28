"""Fail-closed release input gate. Never repairs files or refreshes a lock.

The versioned lock is a reviewed trust root, not protection against an attacker
who can modify both repository code and its trust root. No validation cache or
development override is used. All errors occur before analysis output writes.
"""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ROOT
from .market import FIELDS, SOURCE_URL


class SourceValidationError(ValueError):
    """A release input does not match the reviewed official-source lock."""


def require(condition, field):
    if not condition:
        raise SourceValidationError(f"Source validation failed: {field}")


def checked_file(root, spec):
    relative = Path(spec["path"])
    require(not relative.is_absolute() and ".." not in relative.parts, "unsafe locked path")
    path = root / relative
    require(path.is_file(), f"missing file {relative}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    require(actual == spec["sha256"],
            f"SHA256 {relative}: expected {spec['sha256']}, actual {actual}")
    return path


def read_lock(root):
    path = root / "config/public_source_lock.json"
    require(path.is_file(), "missing config/public_source_lock.json")
    lock = json.loads(path.read_text())
    require(lock["version"] == 1, "unsupported source-lock version")
    return lock


def treasury_observation(path, observation_date):
    tree = ET.parse(path)
    entries = ([tree.getroot()] if tree.getroot().tag.endswith("}entry") else
               tree.getroot().findall("{http://www.w3.org/2005/Atom}entry"))
    rows = []
    for entry in entries:
        row = {e.tag.split("}")[-1]: e.text for e in entry.iter()}
        if str(row.get("NEW_DATE", ""))[:10] == observation_date:
            rows.append(row)
    require(len(rows) == 1, f"Treasury observation_date {observation_date}: expected one row")
    return rows[0]


def verified_curve(root=ROOT, lock=None):
    """Return the consumed curve only after snapshot AND observation checks."""
    root = Path(root)
    lock = read_lock(root) if lock is None else lock
    t = lock["treasury"]
    require(t["official_url"] == SOURCE_URL, "Treasury official_url")
    require(t["units"] == "annual decimal par yield", "Treasury units")
    require(t["observation_date"] == "2026-10-22", "Treasury observation_date")
    raw = checked_file(root, t["raw_snapshot"])
    selected = checked_file(root, t["extracted_observation"])
    for path in (raw, selected):
        row = treasury_observation(path, t["observation_date"])
        for expected in t["expected_rows"]:
            field = expected["source_field"]
            require(field in FIELDS and row.get(field) is not None, f"Treasury missing {field}")
            require(abs(float(row[field]) / 100 - expected["par_rate"]) < 1e-14,
                    f"Treasury raw observation lineage {field}")
    expected = pd.DataFrame(t["expected_rows"])
    for spec in (t["dated_observation"], t["processed_curve"]):
        frame = pd.read_csv(checked_file(root, spec))
        require(list(frame.columns) == list(expected.columns), f"curve schema {spec['path']}")
        require(frame.curve_date.eq(t["observation_date"]).all(), "curve observation_date")
        require(len(frame) == len(FIELDS) and frame.source_field.is_unique,
                "curve maturity set / duplicate tenor")
        require(frame.tenor_years.is_unique and np.all(np.diff(frame.tenor_years) > 0),
                "curve tenor ordering / duplicate tenor")
        require(np.isfinite(frame.par_rate).all() and frame.par_rate.between(0, .25).all(),
                "curve missing rate / annual-decimal range")
        require(np.allclose(frame.tenor_years, t["expected_maturities"], rtol=0, atol=1e-14),
                "curve maturity set")
        require(frame.source_field.tolist() == expected.source_field.tolist() and
                np.allclose(frame.par_rate, expected.par_rate, rtol=0, atol=1e-14),
                "processed curve / raw observation lineage")
    return frame


def validate_sources(root=ROOT):
    """Validate both complete source chains without writing or using old cache."""
    from .public_data import extract_h8, calibration_from_observation, H8_XML, H8_HTML

    root = Path(root)
    lock = read_lock(root)
    curve = verified_curve(root, lock)
    h = lock["h8"]
    require(h["official_url"] == H8_XML and h["release_page_url"] == H8_HTML, "H.8 official_url")
    require(h["units"] == "USD billions" and h["source_units"] == "USD millions", "H.8 units")
    archive = checked_file(root, h["raw_snapshot"])
    html = checked_file(root, h["release_page_snapshot"])
    frame, release, observation, _, _ = extract_h8(archive, html)
    require(release == h["release_date"] and observation == h["observation_date"], "H.8 dates")
    extracted = pd.read_csv(checked_file(root, h["extracted_observation"]))
    require(list(extracted.columns) == list(frame.columns), "H.8 schema")
    require(extracted.field.is_unique and set(extracted.field) == set(h["expected_values"]), "H.8 fields")
    require(extracted.observation_date.eq(observation).all(), "H.8 observation_date")
    require(extracted.units.eq("USD billions").all() and
            extracted.source_units.eq("USD millions").all(), "H.8 extracted units")
    require(extracted.value_usd_billions.between(0, 1e6).all(), "H.8 numeric range / missing value")
    try:
        pd.testing.assert_frame_equal(extracted.sort_values("field").reset_index(drop=True),
                                      frame.sort_values("field").reset_index(drop=True),
                                      check_dtype=False, rtol=0, atol=1e-10)
    except AssertionError as exc:
        raise SourceValidationError(f"H.8 raw / processed lineage mismatch: {exc}") from exc
    values = extracted.set_index("field").value_usd_billions.to_dict()
    require(values == h["expected_values"], "H.8 canonical observation values")
    totals, calibration = calibration_from_observation(frame)
    totals_path = checked_file(root, h["processed_calibration"])
    require(json.loads(totals_path.read_text()) == totals, "H.8 processed calibration / raw lineage")
    cal_path = checked_file(root, h["calibration_table"])
    try:
        pd.testing.assert_frame_equal(pd.read_csv(cal_path), calibration, check_dtype=False, rtol=0, atol=1e-10)
    except AssertionError as exc:
        raise SourceValidationError(f"H.8 calibration table / raw lineage mismatch: {exc}") from exc
    for spec in lock["lineage_metadata"]:
        checked_file(root, spec)
    return {"curve": curve, "h8": frame, "status": "PASS"}


if __name__ == "__main__":
    try:
        validate_sources()
    except (SourceValidationError, KeyError, ValueError, OSError, ET.ParseError) as exc:
        raise SystemExit(f"SOURCE_BINDING_FAIL: {exc}") from exc
    print("SOURCE_BINDING_PASS: Treasury 2026-10-22 and H.8 2026-10-07")
