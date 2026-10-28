"""Saved Office-file acceptance checks independent of the authoring builders."""
import json
import posixpath
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from pathlib import Path
from docx import Document
from pypdf import PdfReader
from PIL import Image
from .config import ROOT
from .controls import check_record

DOC=ROOT/'report/Banking_Book_Interest_Rate_and_Liquidity_Stress_Testing_Report.docx'
XLS=ROOT/'outputs/Bank_Treasury_Risk_Management_Pack.xlsx'
PDF=ROOT/'qa/render/Banking_Book_Interest_Rate_and_Liquidity_Stress_Testing_Report.pdf'
S={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def saved_workbook():
    with ZipFile(XLS) as z:
        assert z.testzip() is None
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rels={r.get('Id'):r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        wb=ET.fromstring(z.read('xl/workbook.xml'))
        sheets={};formulas=[];errors=[];missing_cache=[];table_count=0
        for sheet in wb.findall('s:sheets/s:sheet',S):
            target=rels[sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            filepath=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
            tree=ET.fromstring(z.read(filepath));cells={}
            for c in tree.findall('.//s:sheetData/s:row/s:c',S):
                address=c.get('r');t=c.get('t');v=c.find('s:v',S);f=c.find('s:f',S)
                val=None if v is None else v.text
                if t=='s' and val is not None:val=shared[int(val)]
                elif t=='inlineStr':val=''.join(c.find('s:is',S).itertext())
                elif t=='b':val=val=='1'
                elif t not in ('str','e') and val is not None:
                    try:val=float(val)
                    except ValueError:pass
                cells[address]=val
                if t=='e':errors.append((sheet.get('name'),address,val))
                if f is not None:
                    formulas.append((sheet.get('name'),address,f.text))
                    if v is None or v.text is None:missing_cache.append((sheet.get('name'),address))
            sheets[sheet.get('name')]=cells
            table_count+=len(tree.findall('.//s:tablePart',S))
        charts=[n for n in z.namelist() if re.fullmatch(r'xl/(?:drawings/)?charts/chart\d+\.xml',n)]
        external=[n for n in z.namelist() if 'externalLink' in n or 'connections.xml' in n]
        return dict(sheets=sheets,formulas=formulas,errors=errors,missing_cache=missing_cache,
                    tables=table_count,charts=len(charts),external=external)


def doc_text():
    d=Document(DOC)
    return '\n'.join([p.text for p in d.paragraphs]+[c.text for t in d.tables for row in t.rows for c in row.cells])


def readme_paths():
    links=re.findall(r'\]\(([^)]+)\)',(ROOT/'README.md').read_text())
    return [link for link in links if not link.startswith(('https://','http://','#')) and not (ROOT/link.split('#')[0]).exists()]


def acceptance(require_render=False):
    m=json.loads((ROOT/'outputs/metrics/key_metrics.json').read_text())
    lineage=json.loads((ROOT/'data/processed/public_data_lineage.json').read_text())
    book=saved_workbook();text=doc_text()
    required={'Executive Summary','Balance Sheet','Repricing Gap','NII Scenarios','EVE Scenarios','Liquidity Stress','Assumptions','Data Quality'}
    checks=[check_record('word_docx_openable',DOC.stat().st_size>10000 and bool(text)),
            check_record('excel_xlsx_openable',len(book['sheets'])==12),
            check_record('excel_required_sheets',required.issubset(book['sheets'])),
            check_record('excel_native_tables_charts',book['tables']==15 and book['charts']==4,f"{book['tables']} tables; {book['charts']} charts"),
            check_record('excel_no_external_links',not book['external'],book['external']),
            check_record('excel_no_formula_errors',not book['errors'],book['errors']),
            check_record('excel_formula_caches_present',bool(book['formulas']) and not book['missing_cache'],f"{len(book['formulas'])} formulas"),
            check_record('word_no_unfinished_text',not re.search(r'\b(TODO|TBC|placeholder)\b',text,re.I)),
            check_record('word_no_absolute_local_paths',not re.search(r'/Users/|[A-Za-z]:\\\\',text)),
            check_record('word_no_legacy_equity_proxy_label',not re.search(r'Tier\s*1\s*proxy|EVE\s*/\s*Tier',text,re.I)),
            check_record('word_public_source_hashes',all(r['sha256'] in text for r in lineage['files'])),
            check_record('readme_paths_valid',not readme_paths(),readme_paths())]
    if require_render:
        pages=PdfReader(PDF).pages
        checks.extend([check_record('word_nine_pages',len(pages)==9,len(pages)),
                       check_record('word_no_blank_pages',all(len(p.extract_text())>600 for p in pages))])
    expected={'D7':m['total_assets']/1e6,'D8':m['positions'],'D9':m['base_nii']/1e6,
              'D10':m['worst_delta_nii']/1e6,'D11':m['base_eve']/1e6,
              'D12':m['worst_delta_eve']/1e6,'D13':m['worst_delta_eve_equity_proxy_pct'],
              'D14':90,'D15':m['liquidity_scenarios'][2]['remaining_liquidity_buffer']/1e6,'D16':0}
    error=max(abs(book['sheets']['Executive Summary'][c]-v) for c,v in expected.items())
    checks.append(check_record('excel_core_metrics_vs_python',error<1e-9,f"Max scaled difference {error:.12f}"))
    values=[f"{m['base_nii']/1e6:.3f}",f"{m['base_eve']/1e6:.3f}",f"{m['worst_delta_eve']/1e6:+.3f}",f"{m['worst_delta_nii']/1e6:+.3f}",f"{m['worst_delta_eve_equity_proxy_pct']*100:.1f}%",f"{m['liquidity_scenarios'][2]['remaining_liquidity_buffer']/1e6:.3f}"]
    checks.append(check_record('word_core_metrics_vs_python',all(v in text for v in values)))
    if require_render:
        images=sorted((ROOT/'qa/render').glob('page-*.png'))
        checks.append(check_record('word_page_pngs_present',len(images)==9 and all(Image.open(p).width>=1400 for p in images)))
    with ZipFile(DOC) as z:
        xml=ET.fromstring(z.read('word/styles.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        borders=xml.findall('.//w:pBdr',ns)
        checks.append(check_record('word_title_rule_removed',not borders))
        checks.append(check_record('word_embedded_charts_present',len([n for n in z.namelist() if n.startswith('word/media/')])==4))
    probe=json.loads((ROOT/'qa/workbook_build.json').read_text())
    checks.append(check_record('excel_recalculation_probe',probe['formula_recalculation_probe']=='PASS'))
    workbook_text='\n'.join(str(v) for cells in book['sheets'].values() for v in cells.values() if v is not None)
    checks.append(check_record('excel_no_legacy_equity_proxy_label',not re.search(r'Tier\s*1\s*proxy|EVE\s*/\s*Tier',workbook_text,re.I)))
    return checks


if __name__ == '__main__':
    result=acceptance(require_render=True)
    failed=[check for check in result if check['status']!='PASS']
    print(json.dumps({'status':'FAIL' if failed else 'PASS','checks':len(result),'failed':failed},indent=2))
    if failed:
        raise SystemExit(1)
