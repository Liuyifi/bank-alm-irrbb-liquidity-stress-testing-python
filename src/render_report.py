"""Render the Word management report to PDF and page PNGs for release QA."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import ROOT


DOC = ROOT / "report/Banking_Book_Interest_Rate_and_Liquidity_Stress_Testing_Report.docx"
OUTPUT_DIR = ROOT / "qa/render"


class WordRenderError(RuntimeError):
    """The deterministic local Word-render QA step could not complete."""


def render_tools():
    office = shutil.which("soffice") or shutil.which("libreoffice")
    raster = shutil.which("pdftoppm")
    missing = []
    if office is None:
        missing.append("LibreOffice (soffice)")
    if raster is None:
        missing.append("Poppler (pdftoppm)")
    if missing:
        raise WordRenderError(
            "missing Word-render dependency: " + ", ".join(missing) +
            ". Install the named tools and ensure their executables are on PATH, "
            "then run `python -m src.render_report`.")
    return office, raster


def _run(command, env=None):
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise WordRenderError(
            f"render command failed ({Path(command[0]).name}): {detail[-2000:]}")


def render(doc=DOC, output_dir=OUTPUT_DIR):
    """Render *doc* atomically into *output_dir* using local CLI tools."""
    doc = Path(doc).resolve()
    output_dir = Path(output_dir).resolve()
    if not doc.is_file():
        raise WordRenderError(f"Word report not found: {doc}")
    office, raster = render_tools()

    with tempfile.TemporaryDirectory(prefix="alm-word-render-") as temp:
        temp_root = Path(temp)
        work = temp_root / "output"
        profile = temp_root / "libreoffice-profile"
        home = temp_root / "home"
        work.mkdir(); profile.mkdir(); home.mkdir()
        env = os.environ.copy()
        env["HOME"] = str(home)
        _run([office, "--headless", f"-env:UserInstallation={profile.as_uri()}",
              "--convert-to", "pdf", "--outdir", str(work), str(doc)], env=env)
        pdf = work / f"{doc.stem}.pdf"
        if not pdf.is_file() or pdf.stat().st_size == 0:
            raise WordRenderError("LibreOffice reported success but produced no PDF")
        _run([raster, "-png", "-r", "180", str(pdf), str(work / "page")])
        pages = sorted(work.glob("page-*.png"))
        if not pages:
            raise WordRenderError("Poppler reported success but produced no page PNGs")

        output_dir.mkdir(parents=True, exist_ok=True)
        target_pdf = output_dir / pdf.name
        shutil.copy2(pdf, target_pdf)
        for old in output_dir.glob("page-*.png"):
            old.unlink()
        for page in pages:
            shutil.copy2(page, output_dir / page.name)
    return target_pdf, sorted(output_dir.glob("page-*.png"))


if __name__ == "__main__":
    try:
        pdf, pages = render()
    except WordRenderError as exc:
        raise SystemExit(f"WORD_RENDER_FAIL: {exc}") from exc
    print(f"WORD_RENDER_PASS: {pdf} ({len(pages)} pages)")
