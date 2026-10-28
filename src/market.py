"""Official curve ingestion and transparent par-to-discount bootstrap."""
import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
import urllib.request
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from .config import ROOT, AS_OF, CURVE_FLOOR

SOURCE_URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
              "pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=2026")
PAGE_URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            "TextView?type=daily_treasury_yield_curve&field_tdr_date_value=2026")
FIELDS = {"BC_1MONTH": 1/12, "BC_2MONTH": 2/12, "BC_3MONTH": .25,
          "BC_4MONTH": 1/3, "BC_6MONTH": .5, "BC_1YEAR": 1.,
          "BC_2YEAR": 2., "BC_3YEAR": 3., "BC_5YEAR": 5.,
          "BC_7YEAR": 7., "BC_10YEAR": 10., "BC_20YEAR": 20., "BC_30YEAR": 30.}


_VERIFIED_CURVE_TOKEN = object()


@dataclass(frozen=True)
class _CurveBinding:
    """Opaque proof that a Curve was created from the validated release source."""

    token: object
    scenario: str


def snapshot(xml_path=None, allow_fallback=False):
    """Persist one unmodified source entry, derived nodes and auditable lineage."""
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    failure = None
    try:
        payload = (open(xml_path, "rb").read() if xml_path else
                   urllib.request.urlopen(SOURCE_URL, timeout=40).read())
        tree = ET.fromstring(payload)
        eligible = []
        for entry in tree.findall("{http://www.w3.org/2005/Atom}entry"):
            data = {e.tag.split("}")[-1]: e.text for e in entry.iter()}
            date = str(data.get("NEW_DATE", ""))[:10]
            if date and date <= AS_OF and all(data.get(f) for f in FIELDS):
                eligible.append((date, entry, data))
        if not eligible:
            raise ValueError("No complete official curve on or before the valuation date")
        date, entry, data = max(eligible, key=lambda x: x[0])
        (raw / "treasury_annual_source.xml").write_bytes(payload)
        # Treasury percent quotes become decimal annual par rates.
        nodes = [(f, t, float(data[f])/100) for f, t in FIELDS.items()]
        (raw / "treasury_selected_entry.xml").write_bytes(ET.tostring(entry, encoding="utf-8", xml_declaration=True))
        source_type = "Official US Treasury par yield curve"
    except Exception as exc:
        if not allow_fallback:
            raise
        failure = f"{type(exc).__name__}: {exc}"
        date = AS_OF
        vals = [.041, .041, .041, .041, .0405, .04, .039, .039, .04, .041, .042, .044, .044]
        nodes = [(f, t, y) for (f, t), y in zip(FIELDS.items(), vals)]
        source_type = "ILLUSTRATIVE built-in curve; official download failed"
    frame = pd.DataFrame(nodes, columns=["source_field", "tenor_years", "par_rate"])
    frame.insert(0, "curve_date", date)
    frame.to_csv(raw / "treasury_curve.csv", index=False)
    frame.to_csv(raw / f"treasury_yield_curve_{date}.csv", index=False)
    lineage = dict(source_type=source_type, source_url=SOURCE_URL, display_url=PAGE_URL,
                   curve_date=date, valuation_date=AS_OF,
                   observation_date=date,
                   publication_date=None if failure else data.get("updated","")[:10],
                   publication_date_definition="Selected Atom entry updated timestamp date; not a separate claim about market-close publication time",
                   feed_updated_timestamp=None if failure else data.get("updated"),
                   download_date=datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                   latest_policy="Latest complete curve dated <= valuation date in the annual official response",
                   lag_calendar_days=(pd.Timestamp(AS_OF)-pd.Timestamp(date)).days,
                   fields={"curve_date": "Treasury NEW_DATE, ISO date", "tenor_years": "Months/12 or years",
                           "par_rate": "Official percent quote divided by 100, annual decimal",
                           "source_field": "Original Treasury XML field"},
                   source_response_sha256=None if failure else hashlib.sha256(payload).hexdigest(),
                   snapshot_sha256=hashlib.sha256((raw / "treasury_selected_entry.xml").read_bytes()).hexdigest() if not failure else None,
                   failure=failure,
                   important="Par rates are bootstrapped using an approximate synthetic semiannual convention; they are not observed zero rates or SOFR.")
    (raw / "curve_lineage.json").write_text(json.dumps(lineage, indent=2))
    return lineage


def shock(tenor, scenario):
    t = np.asarray(tenor, dtype=float)
    parallel = {"Base": 0., "Parallel up 100 bps": .01, "Parallel up 200 bps": .02,
                "Parallel down 100 bps": -.01, "Parallel down 200 bps": -.02}
    if scenario in parallel:
        return np.full_like(t, parallel[scenario])
    twist = .01 * (1 - 2*np.exp(-t/4))
    if scenario == "Steepener":
        return twist
    if scenario == "Flattener":
        return -twist
    raise ValueError(scenario)


class Curve:
    """Immutable piecewise log-linear discount curve.

    Direct construction is intentionally unbound and remains useful for generic
    bootstrap analysis. Production cash-flow/EVE calculations must use
    :meth:`from_verified_source`, whose source binding is rechecked at the
    computational boundary.
    """

    __slots__ = ("_node_t", "_par", "_times", "_dfs", "_scenario", "_binding")

    def __init__(self, nodes, scenario="Base"):
        node_t = nodes.tenor_years.to_numpy(float)
        par = np.maximum(nodes.par_rate.to_numpy(float) + shock(node_t, scenario), CURVE_FLOOR)
        short = node_t[node_t < .5]
        times = [0.] + short.tolist()
        dfs = [1.] + (1/(1 + np.interp(short, node_t, par)*short)).tolist()
        semi_dfs = []
        for t in np.arange(.5, 30.01, .5):
            c = np.interp(t, node_t, par)
            df = (1 - .5*c*sum(semi_dfs))/(1+.5*c)
            if df <= 0:
                raise ValueError("Bootstrap produced a nonpositive discount factor")
            semi_dfs.append(df)
            times.append(float(t)); dfs.append(float(df))
        if np.any(np.diff(dfs) > 1e-10):
            raise ValueError("Negative implied forward rate under configured positive-rate scenarios")

        object.__setattr__(self, "_node_t", tuple(float(x) for x in node_t))
        object.__setattr__(self, "_par", tuple(float(x) for x in par))
        object.__setattr__(self, "_times", tuple(float(x) for x in times))
        object.__setattr__(self, "_dfs", tuple(float(x) for x in dfs))
        object.__setattr__(self, "_scenario", scenario)
        object.__setattr__(self, "_binding", None)

    def __setattr__(self, name, value):
        raise AttributeError("Curve is immutable; construct a new verified curve")

    def __copy__(self):
        clone = object.__new__(type(self))
        for name in self.__slots__:
            object.__setattr__(clone, name, getattr(self, name))
        return clone

    def __deepcopy__(self, memo):
        clone = self.__copy__()
        memo[id(self)] = clone
        return clone

    @property
    def node_t(self):
        return np.array(self._node_t)

    @property
    def par(self):
        return np.array(self._par)

    @property
    def times(self):
        return np.array(self._times)

    @property
    def dfs(self):
        return np.array(self._dfs)

    @property
    def scenario(self):
        return self._scenario

    @classmethod
    def from_verified_source(cls, scenario="Base"):
        """Build an immutable Curve from the currently validated source lock."""
        from .source_validation import verified_curve

        curve = cls(verified_curve(), scenario)
        object.__setattr__(curve, "_binding", _CurveBinding(
            token=_VERIFIED_CURVE_TOKEN, scenario=scenario))
        return curve

    def df(self, t):
        return np.exp(np.interp(t, self._times, np.log(self._dfs)))

    def forward(self, start, end):
        if end <= start:
            raise ValueError("Forward end must exceed start")
        return float((self.df(start)/self.df(end)-1)/(end-start))


def require_source_bound_curve(curve, scenario):
    """Authorize a canonical Curve for sensitive production calculations.

    This module-owned boundary deliberately avoids virtual dispatch.  It accepts
    only the exact production type, revalidates the locked source, reconstructs
    the expected curve, and compares every current normalized numeric field.
    """
    from .source_validation import SourceValidationError, verified_curve

    if type(curve) is not Curve:
        raise SourceValidationError(
            "Cash-flow calculation requires the canonical concrete Curve type")

    binding = object.__getattribute__(curve, "_binding")
    if (type(binding) is not _CurveBinding or
            object.__getattribute__(binding, "token") is not _VERIFIED_CURVE_TOKEN):
        raise SourceValidationError(
            "Curve is not source-bound; use Curve.from_verified_source()")

    bound_scenario = object.__getattribute__(binding, "scenario")
    curve_scenario = object.__getattribute__(curve, "_scenario")
    if (type(bound_scenario) is not str or type(curve_scenario) is not str or
            bound_scenario != curve_scenario):
        raise SourceValidationError("Curve provenance scenario is invalid")
    if type(scenario) is not str or scenario != curve_scenario:
        raise SourceValidationError("Cash-flow scenario does not match Curve provenance")

    canonical_nodes = verified_curve()
    expected = Curve(canonical_nodes, bound_scenario)
    for name in ("_node_t", "_par", "_times", "_dfs"):
        current_values = object.__getattribute__(curve, name)
        expected_values = object.__getattribute__(expected, name)
        if (type(current_values) is not tuple or
                not all(type(value) is float for value in current_values) or
                current_values != expected_values):
            raise SourceValidationError(
                "Curve in-memory integrity does not match its verified source binding")
    return canonical_nodes


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--xml")
    p.add_argument("--allow-fallback", action="store_true")
    a = p.parse_args()
    print(json.dumps(snapshot(a.xml, a.allow_fallback), indent=2))
