import json
from zipfile import ZipFile
import pytest
from src.config import ROOT
from src.artifact_validation import DOC,XLS,acceptance,doc_text,saved_workbook,readme_paths
from src.render_report import WordRenderError,render_tools


def test_saved_office_packages_open():
    for file in (DOC,XLS):
        with ZipFile(file) as z:
            assert z.testzip() is None
    assert len(doc_text())>10000
    assert len(saved_workbook()['sheets'])==12


def test_saved_formulas_and_native_features():
    book=saved_workbook()
    assert book['charts']==4 and book['tables']>=8
    assert not book['errors'] and not book['missing_cache']


def test_report_contains_full_public_source_hashes():
    source=json.loads((ROOT/'data/processed/public_data_lineage.json').read_text())
    assert all(f['sha256'] in doc_text() for f in source['files'])


def test_all_final_artifact_controls():
    assert all(c['status']=='PASS' for c in acceptance())


def test_readme_targets_exist():
    assert not readme_paths()


def test_word_render_dependency_failure_is_actionable(monkeypatch):
    monkeypatch.setattr('src.render_report.shutil.which',lambda name: None)
    with pytest.raises(WordRenderError,match='LibreOffice.*Poppler.*python -m src.render_report'):
        render_tools()
