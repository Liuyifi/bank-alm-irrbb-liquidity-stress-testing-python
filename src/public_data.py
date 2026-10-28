"""Download and freeze official public inputs. Offline use is the default later.

The H.8 XML archive is preferred. The official current HTML is retained for a
release-date and rounded-table cross-check, and is a parser fallback if XML fails.
No unofficial source or hand-entered fallback is silently used.
"""
import argparse
import hashlib
import io
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo
import pandas as pd
from .config import ROOT, AS_OF
from .market import snapshot, SOURCE_URL

H8_XML = "https://www.federalreserve.gov/releases/h8/data/FRB_h8_xml.zip"
H8_HTML = "https://www.federalreserve.gov/releases/h8/current/default.htm"
ITEMS = {"1002":"securities", "1020":"loans", "1048":"cash_assets",
         "1151":"total_assets", "1058":"deposits", "3094":"borrowings",
         "1100":"net_due_foreign", "3095":"other_liabilities",
         "1152":"total_liabilities", "1091":"residual_equity_proxy"}
HTML_ROWS = {2:"securities",9:"loans",29:"cash_assets",33:"total_assets",34:"deposits",
             37:"borrowings",38:"net_due_foreign",39:"other_liabilities",
             40:"total_liabilities",41:"residual_equity_proxy"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class H8Table(HTMLParser):
    def __init__(self):
        super().__init__(); self.cells={}; self.active=None; self.buf=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag in ("th","td"):
            ident=attrs.get("id",""); heads=attrs.get("headers","")
            if ident.startswith("h8t3") or "h8t3b4" in heads:
                self.active=ident or heads; self.buf=[]
    def handle_data(self, data):
        if self.active is not None: self.buf.append(data)
    def handle_endtag(self, tag):
        if tag in ("th","td") and self.active is not None:
            self.cells[self.active]=" ".join(" ".join(self.buf).split()); self.active=None


def parse_html(payload):
    text=payload.decode("utf-8")
    release=pd.Timestamp(re.search(r"Release Date:\s*([A-Za-z]+ \d{1,2}, \d{4})",text).group(1)).date().isoformat()
    parser=H8Table(); parser.feed(text)
    observation=pd.Timestamp(parser.cells["h8t3b4"]+" "+release[:4]).date().isoformat()
    values={}
    for row,field in HTML_ROWS.items():
        key=next(k for k in parser.cells if "h8t3b4" in k and f"h8t3r{row}b" in k.split())
        values[field]=float(parser.cells[key].replace(",",""))
    return release,observation,values


def extract_h8(zip_path, html_path):
    """Select all-commercial-bank, weekly Wednesday, NSA levels, million USD."""
    release,observation,html_values=parse_html(html_path.read_bytes())
    if release > AS_OF or observation > AS_OF:
        raise ValueError("H.8 snapshot is newer than the locked run date; obtain dated official release")
    if zip_path is None:
        rows=[dict(field=f,series_name=f"h8t3r{r}",observation_date=observation,
                   value_usd_billions=html_values[f],source_units="USD billions",units="USD billions",
                   seasonal_adjustment="Not seasonally adjusted",description=f"Official Table 3 row {r}")
              for r,f in HTML_ROWS.items()]
        return pd.DataFrame(rows),release,observation,0.,"official current HTML parser"
    rows=[]; prepared=None
    z=zipfile.ZipFile(zip_path)
    for _,e in ET.iterparse(z.open("H8_data.xml"),events=["end"]):
        if e.tag.endswith("}Prepared"):
            prepared=e.text
        if e.tag.endswith("}Series"):
            a=e.attrib
            if (a.get("BG")=="CB" and a.get("SA")=="NSA" and a.get("FREQ")=="19"
                and a.get("H8_UNITS")=="LEVEL" and a.get("ITEM") in ITEMS):
                obs=[x.attrib for x in e if x.tag.endswith("}Obs") and x.get("TIME_PERIOD")==observation]
                if not obs: raise ValueError(f"Missing H.8 observation {a}")
                if a.get("UNIT_MULT") != "1000000": raise ValueError("Unexpected H.8 unit multiplier")
                desc=next(x.text for x in e.iter() if x.tag.endswith("}AnnotationText"))
                rows.append(dict(field=ITEMS[a["ITEM"]],series_name=a["SERIES_NAME"],observation_date=observation,
                                 value_usd_billions=float(obs[0]["OBS_VALUE"])/1000,
                                 source_units="USD millions",units="USD billions",seasonal_adjustment="Not seasonally adjusted",description=desc))
            e.clear()
    if prepared[:10]!=release: raise ValueError("XML archive and HTML release vintages differ")
    frame=pd.DataFrame(rows)
    if set(frame.field)!=set(ITEMS.values()): raise ValueError("Incomplete H.8 required fields")
    discrepancy=max(abs(r.value_usd_billions-html_values[r.field]) for r in frame.itertuples())
    if discrepancy > .051: raise ValueError("H.8 XML/HTML values exceed table rounding tolerance")
    return frame,release,observation,discrepancy,"official downloadable XML archive"


def download(url,path):
    request=urllib.request.Request(url,headers={"User-Agent":"BankALMResearch/1.0 public portfolio project"})
    with urllib.request.urlopen(request,timeout=60) as response:
        if response.geturl().split("/")[2] not in ("home.treasury.gov","www.federalreserve.gov"):
            raise ValueError("Unexpected nonofficial redirect")
        payload=response.read()
    if not payload: raise ValueError("Empty official response")
    path.write_bytes(payload)


def acquire(refresh=False):
    from .source_validation import validate_sources, SourceValidationError
    if refresh:
        raise SourceValidationError("Locked release forbids refresh; acquire a new vintage in a separate project and explicitly review/version the source lock")
    validate_sources()
    raw=ROOT/"data/raw"; raw.mkdir(parents=True,exist_ok=True)
    lineage_path=ROOT/"data/processed/public_data_lineage.json"
    if lineage_path.exists() and not refresh:
        old=json.loads(lineage_path.read_text())
        for item in old["files"]:
            if sha(ROOT/item["path"])!=item["sha256"]: raise ValueError("Frozen source hash mismatch")
        return old
    attempts=[]
    treasury=raw/"treasury_annual_source.xml"
    download(SOURCE_URL,treasury)
    t=snapshot(treasury)
    html=raw/"federal_reserve_h8_current_source.html"
    archive=raw/"federal_reserve_h8_source.zip"
    try:
        download(H8_XML,archive)
        attempts.append(dict(url=H8_XML,status="success"))
    except Exception as exc:
        attempts.append(dict(url=H8_XML,status="failed",error=str(exc))); archive=None
    download(H8_HTML,html)
    try:
        frame,release,observation,diff,mode=extract_h8(archive,html)
    except (ValueError,ET.ParseError,zipfile.BadZipFile) as exc:
        attempts.append(dict(url=H8_XML,status="parse failed",error=str(exc)))
        frame,release,observation,diff,mode=extract_h8(None,html)
    output=raw/f"federal_reserve_h8_{release}.csv"
    frame.to_csv(output,index=False)
    files=[treasury,raw/"treasury_selected_entry.xml",raw/f"treasury_yield_curve_{t['curve_date']}.csv",html,output]
    if archive: files.append(archive)
    lineage=dict(run_date=AS_OF,download_time=datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                 treasury=t,h8=dict(source_type=mode,source_url=H8_XML if mode=='official downloadable XML archive' else H8_HTML,
                                    release_page=H8_HTML,release_date=release,observation_date=observation,
                                    units="USD billions after converting XML USD millions / 1000",
                                    seasonal_adjustment="Not seasonally adjusted",population="All commercial banks in the United States",
                                    xml_html_max_difference_usd_billions=diff,
                                    field_mapping=frame[["field","series_name","description"]].to_dict("records"),
                                    attempts=attempts),
                 fallback_used=False,
                 files=[dict(path=str(f.relative_to(ROOT)),bytes=f.stat().st_size,sha256=sha(f)) for f in files])
    lineage_path.write_text(json.dumps(lineage,indent=2))
    return lineage


def calibration_from_observation(f):
    """Pure, cent-exact public-share transformation, also verified before writes."""
    x=f.set_index("field").value_usd_billions.to_dict()
    total=x["total_assets"]; scale=100_000_000/total
    groups={"cash_assets":x["cash_assets"],"securities":x["securities"],"loans":x["loans"],
            "other_assets_net":total-x["cash_assets"]-x["securities"]-x["loans"],
            "deposits":x["deposits"],"borrowings":x["borrowings"],
            "other_liabilities_net":x["other_liabilities"]+x["net_due_foreign"],
            "residual_equity_proxy":x["residual_equity_proxy"]}
    cents={k:round(v*scale*100) for k,v in groups.items()}
    cents["other_assets_net"]=10_000_000_000-sum(cents[k] for k in ("cash_assets","securities","loans"))
    cents["other_liabilities_net"]=10_000_000_000-sum(cents[k] for k in ("deposits","borrowings","residual_equity_proxy"))
    loan_m=round(cents["loans"]*40/75); loan_c=round(cents["loans"]*25/75)
    nmd=round(cents["deposits"]*55/75)
    totals={"Fixed-rate mortgages":loan_m/100,"Floating-rate corporate loans":loan_c/100,
            "Consumer loans":(cents["loans"]-loan_m-loan_c)/100,"Government securities":cents["securities"]/100,
            "Cash and liquid assets":cents["cash_assets"]/100,
            "Non-maturity retail deposits":nmd/100,"Term deposits":(cents["deposits"]-nmd)/100,
            "Wholesale funding":cents["borrowings"]/100,"H.8 residual-based equity proxy":cents["residual_equity_proxy"]/100,
            "Other non-rate-sensitive assets":cents["other_assets_net"]/100,
            "Other non-rate-sensitive liabilities":cents["other_liabilities_net"]/100}
    mapping={"cash_assets":["Cash and liquid assets"],"securities":["Government securities"],
             "loans":["Fixed-rate mortgages","Floating-rate corporate loans","Consumer loans"],
             "other_assets_net":["Other non-rate-sensitive assets"],
             "deposits":["Non-maturity retail deposits","Term deposits"],"borrowings":["Wholesale funding"],
             "other_liabilities_net":["Other non-rate-sensitive liabilities"],"residual_equity_proxy":["H.8 residual-based equity proxy"]}
    records=[]
    for group,value in groups.items():
        actual=sum(totals[p] for p in mapping[group])
        records.append(dict(group=group,side="asset" if group in list(groups)[:4] else "funding",
                            observed_usd_billions=value,target_pct_total_assets=value/total,
                            synthetic_usd=actual,synthetic_pct_total_assets=actual/1e8,
                            difference_pct_points=(actual/1e8-value/total)*100,tolerance_pct_points=.01,
                            synthetic_products="; ".join(mapping[group])))
    return totals, pd.DataFrame(records)


def calibrate():
    from .source_validation import validate_sources
    verified = validate_sources()
    totals, records = calibration_from_observation(verified["h8"])
    records.to_csv(ROOT/"outputs/tables/h8_balance_sheet_calibration.csv",index=False)
    (ROOT/"data/processed/calibrated_product_totals.json").write_text(json.dumps(totals,indent=2))
    return totals


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--refresh",action="store_true")
    args=parser.parse_args(); result=acquire(args.refresh); calibrate()
    print(json.dumps({"Treasury":result["treasury"]["curve_date"],"H8_release":result["h8"]["release_date"],
                      "H8_observation":result["h8"]["observation_date"],"fallback_used":result["fallback_used"]},indent=2))
