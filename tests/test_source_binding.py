"""Adversarial release-entry tests run only in disposable isolated projects."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.config import ROOT
from src.source_validation import SourceValidationError, validate_sources, verified_curve


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('outputs','report','data/processed') for p in (root/folder).rglob('*') if p.is_file()}


@pytest.fixture
def isolated(tmp_path):
    for folder in ('src','config','data/raw'):
        shutil.copytree(ROOT/folder,tmp_path/folder,ignore=shutil.ignore_patterns('__pycache__'))
    for relative in ('data/processed/calibrated_product_totals.json','data/processed/public_data_lineage.json',
                     'outputs/tables/h8_balance_sheet_calibration.csv'):
        dest=tmp_path/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,dest)
    (tmp_path/'outputs/KEEP_OLD_OUTPUT.txt').write_text('Existing output must stay unchanged on failure')
    (tmp_path/'report').mkdir();(tmp_path/'report/KEEP_OLD_REPORT.txt').write_text('old report')
    return tmp_path


def mutate(root,case):
    path=root/'data/raw/treasury_curve.csv'
    f=pd.read_csv(path)
    if case=='ten_bp': f['par_rate']+=.001
    elif case=='one_bp': f.loc[4,'par_rate']+=.0001
    elif case=='date': f['curve_date']='2026-10-21'
    elif case=='missing_tenor': f=f.iloc[:-1]
    elif case=='h8_input':
        path=root/'data/raw/federal_reserve_h8_2026-10-16.csv'
        f=pd.read_csv(path);f.loc[0,'value_usd_billions']+=1
    elif case=='raw_lineage':
        path=root/'data/raw/treasury_selected_entry.xml'
        text=path.read_text().replace('3.79','3.80')
        # Change an actual node and update only its byte hash; semantic gate must still fail.
        import xml.etree.ElementTree as ET
        tree=ET.parse(path)
        node=next(e for e in tree.iter() if e.tag.endswith('}BC_1YEAR'))
        node.text=str(float(node.text)+.01);tree.write(path,encoding='utf-8',xml_declaration=True)
        lock_path=root/'config/public_source_lock.json';lock=json.loads(lock_path.read_text())
        lock['treasury']['extracted_observation']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        lock_path.write_text(json.dumps(lock));return
    elif case=='missing_lock':
        (root/'config/public_source_lock.json').unlink();return
    else: raise AssertionError(case)
    f.to_csv(path,index=False)


@pytest.mark.parametrize('case',['ten_bp','one_bp','date','missing_tenor','h8_input','raw_lineage','missing_lock'])
def test_pipeline_rejects_before_eve_and_preserves_outputs(isolated,case):
    mutate(isolated,case)
    before=hashes(isolated)
    # This marker proves the EVE function is never entered, even on the 10bp attack.
    with (isolated/'src/engine.py').open('a') as file:
        file.write('\n_original_run_ir = run_ir\ndef run_ir(*a, **k):\n    from pathlib import Path\n    Path("EVE_ENTERED").write_text("unexpected")\n    return _original_run_ir(*a, **k)\n')
    result=subprocess.run([sys.executable,'-m','src.pipeline'],cwd=isolated,capture_output=True,text=True)
    assert result.returncode!=0
    assert 'Source validation failed' in result.stderr
    assert not (isolated/'EVE_ENTERED').exists()
    assert hashes(isolated)==before
    if case=='ten_bp': assert 'SHA256 data/raw/treasury_curve.csv' in result.stderr


@pytest.mark.parametrize('entry',['src.public_data','src.figures','src.prepare_artifacts','src.write_documentation','src.build_report','src.final_qa'])
def test_artifact_entries_cannot_publish_with_corrupt_source(isolated,entry):
    mutate(isolated,'ten_bp');before=hashes(isolated)
    result=subprocess.run([sys.executable,'-m',entry],cwd=isolated,capture_output=True,text=True)
    assert result.returncode!=0 and 'Source validation failed' in result.stderr
    assert hashes(isolated)==before


def test_semantic_checks_survive_rehashed_bad_curve(isolated):
    f=pd.read_csv(isolated/'data/raw/treasury_curve.csv');f.loc[1,'tenor_years']=f.loc[0,'tenor_years']
    path=isolated/'data/raw/treasury_curve.csv';f.to_csv(path,index=False)
    lp=isolated/'config/public_source_lock.json';lock=json.loads(lp.read_text())
    lock['treasury']['processed_curve']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();lp.write_text(json.dumps(lock))
    with pytest.raises(SourceValidationError,match='ordering / duplicate tenor'): verified_curve(isolated)


def test_replaced_processed_calibration_rejected(isolated):
    p=isolated/'data/processed/calibrated_product_totals.json';d=json.loads(p.read_text());d['Cash and liquid assets']+=1;p.write_text(json.dumps(d))
    with pytest.raises(SourceValidationError,match='SHA256 data/processed/calibrated_product_totals.json'): validate_sources(isolated)
