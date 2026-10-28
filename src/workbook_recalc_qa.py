"""Force LibreOffice recalculation on a disposable XLSX and verify the saved file."""
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from openpyxl import load_workbook

from .config import ROOT


XLSX = ROOT / "outputs/Bank_Treasury_Risk_Management_Pack.xlsx"
QA = ROOT / "qa/release_fix_20261023"
SOFFICE = os.environ.get("SOFFICE") or shutil.which("soffice")
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def cache_stripped(source, target):
    removed = 0
    with zipfile.ZipFile(source) as zin:
        entries = {name: zin.read(name) for name in zin.namelist()}
    for name, payload in list(entries.items()):
        if not name.startswith("xl/worksheets/sheet") or not name.endswith(".xml"):
            continue
        tree = ET.fromstring(payload)
        for cell in tree.iter(S + "c"):
            if cell.find(S + "f") is None:
                continue
            value = cell.find(S + "v")
            if value is not None:
                cell.remove(value)
                removed += 1
        entries[name] = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
    workbook = ET.fromstring(entries["xl/workbook.xml"])
    calc = workbook.find(S + "calcPr")
    if calc is None:
        calc = ET.SubElement(workbook, S + "calcPr")
    calc.set("calcMode", "auto")
    calc.set("fullCalcOnLoad", "1")
    calc.set("forceFullCalc", "1")
    entries["xl/workbook.xml"] = ET.tostring(workbook, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, payload in entries.items():
            zout.writestr(name, payload)
    return removed


def structure(path):
    book = load_workbook(path, data_only=False, read_only=False)
    values = load_workbook(path, data_only=True, read_only=False)
    errors = []
    missing = []
    formulas = 0
    for sheet in book:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.data_type == "f":
                    formulas += 1
                    if values[sheet.title][cell.coordinate].value is None:
                        missing.append(f"{sheet.title}!{cell.coordinate}")
                if cell.data_type == "e":
                    errors.append(f"{sheet.title}!{cell.coordinate}: {cell.value}")
    return {
        "sheets": len(book.sheetnames),
        "tables": sum(len(sheet.tables) for sheet in book),
        "charts": sum(len(sheet._charts) for sheet in book),
        "formulas": formulas,
        "errors": errors,
        "missing_formula_caches": missing,
        "external_links": len(book._external_links),
    }


def run():
    if not SOFFICE:
        raise RuntimeError("Set SOFFICE to the workspace dependency loader's LibreOffice executable")
    QA.mkdir(parents=True, exist_ok=True)
    before = structure(XLSX)
    with TemporaryDirectory(prefix="alm-xlsx-recalc-") as temp_name:
        temp = Path(temp_name)
        uncached = temp / XLSX.name
        removed = cache_stripped(XLSX, uncached)
        out = temp / "recalculated"
        out.mkdir()
        profile = temp / "lo-profile"
        command = [SOFFICE, f"-env:UserInstallation={profile.as_uri()}", "--headless",
                   "--convert-to", "xlsx", "--outdir", str(out), str(uncached)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        recalculated = out / XLSX.name
        if result.returncode or not recalculated.is_file():
            raise RuntimeError(f"LibreOffice recalculation failed: {result.stdout}\n{result.stderr}")
        after = structure(recalculated)
        shutil.copy2(recalculated, QA / "libreoffice_recalculated.xlsx")
    passed = (removed == before["formulas"] and after["sheets"] == 12 and
              after["tables"] == 15 and after["charts"] == 4 and
              after["formulas"] >= before["formulas"] and not after["errors"] and
              not after["missing_formula_caches"] and not after["external_links"])
    version = subprocess.run([SOFFICE, "--version"], capture_output=True,
                             text=True, timeout=30).stdout.strip()
    evidence = {"status": "PASS" if passed else "FAIL", "cache_values_removed": removed,
                "before": before, "after_libreoffice": after, "libreoffice_version": version}
    (QA / "excel_libreoffice_qa.json").write_text(json.dumps(evidence, indent=2) + "\n")
    if not passed:
        raise AssertionError(evidence)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    run()
