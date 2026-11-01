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


def ensure_word_render():
    """Create missing or stale Word visual-QA evidence before validation."""
    images=sorted((ROOT/'qa/render').glob('page-*.png'))
    current=PDF.is_file() and images and min([PDF.stat().st_mtime]+[p.stat().st_mtime for p in images])>=DOC.stat().st_mtime
    if not current:
        from .render_report import render
        render()


def acceptance(require_render=False):
    if require_render:
        ensure_word_render()
    m=json.loads((ROOT/'outputs/metrics/key_metrics.json').read_text())
    book=saved_workbook();text=doc_text()
    properties=Document(DOC).core_properties
    expected_subject='Recruitment Portfolio Case Study in Treasury Risk, ALM, IRRBB and Liquidity Stress Testing'
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
            check_record('word_portfolio_identity',all(value in text for value in ('YIFEI LIU\'S PORTFOLIO CASE STUDY','Yifei Liu','Target roles','Core stack','Risk focus'))),
            check_record('word_recruitment_polish',all(value in text for value in ('Python | SQL | DuckDB | Excel','ALM | IRRBB | Liquidity Stress Testing','Portfolio evidence','ANALYTICAL WORKFLOW','Official Public Sources','Risk communication & reporting','≥90 Days','≥90 days')) and not re.search(r'Recruiter view|Recruiter takeaway',text,re.I)),
            check_record('word_repository_visible','https://github.com/Liuyifi/bank-alm-irrbb-liquidity-stress-testing-python' in text),
            check_record('word_public_source_context',all(value in text for value in ('Federal Reserve H.8','US Treasury'))),
            check_record('word_model_boundaries',all(value in text for value in ('synthetic portfolio study','not regulatory capital','not a BCBS supervisory outlier test','no formal LCR or NSFR'))),
            check_record('word_core_properties_author',properties.author=='Yifei Liu' and properties.last_modified_by=='Yifei Liu' and properties.title=='Bank ALM / IRRBB & Liquidity Stress Testing'),
            check_record('word_core_properties_clean',properties.subject==expected_subject and not properties.comments and not properties.keywords and not properties.category),
            check_record('word_no_ai_branding',not re.search(r'ChatGPT|Codex|OpenAI',text,re.I)),
            check_record('readme_paths_valid',not readme_paths(),readme_paths())]
    if require_render:
        pages=PdfReader(PDF).pages
        checks.extend([check_record('word_page_count_exact',len(pages)==9,len(pages)),
                       check_record('word_no_blank_pages',all(len(p.extract_text())>600 for p in pages))])
    expected={'D7':m['total_assets']/1e6,'D8':m['positions'],'D9':m['base_nii']/1e6,
              'D10':m['worst_delta_nii']/1e6,'D11':m['base_eve']/1e6,
              'D12':m['worst_delta_eve']/1e6,'D13':m['worst_delta_eve_equity_proxy_pct'],
              'D14':90,'D15':m['liquidity_scenarios'][2]['remaining_liquidity_buffer']/1e6,'D16':0}
    error=max(abs(book['sheets']['Executive Summary'][c]-v) for c,v in expected.items())
    checks.append(check_record('excel_core_metrics_vs_python',error<1e-9,f"Max scaled difference {error:.12f}"))
    values=[f"{m['base_nii']/1e6:.3f}",f"{m['base_eve']/1e6:.3f}",f"{m['worst_delta_eve']/1e6:+.3f}",f"{m['worst_delta_nii']/1e3:+.1f}",f"{m['worst_delta_eve_equity_proxy_pct']*100:.2f}%",f"{m['liquidity_scenarios'][2]['remaining_liquidity_buffer']/1e6:.3f}"]
    checks.append(check_record('word_core_metrics_vs_python',all(v in text for v in values)))
    if require_render:
        images=sorted((ROOT/'qa/render').glob('page-*.png'))
        checks.append(check_record('word_page_pngs_present',len(images)==len(pages)==9 and all(Image.open(p).width>=1400 for p in images)))
    with ZipFile(DOC) as z:
        package_names=z.namelist()
        banned_terms=(b'codex',b'openai',b'chatgpt',b'python-docx')
        package_hits={term.decode():[name for name in package_names if term in z.read(name).lower()] for term in banned_terms}
        review_parts=[name for name in package_names if re.search(r'(?:^|/)(?:comments[^/]*|people|persons)\.xml$',name,re.I)]
        xml=ET.fromstring(z.read('word/styles.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        borders=xml.findall('.//w:pBdr',ns)
        document_xml=z.read('word/document.xml').decode('utf-8')
        media=[n for n in z.namelist() if n.startswith('word/media/')]
        checks.append(check_record('word_title_rule_removed',not borders))
        checks.append(check_record('word_embedded_visuals_present',len(media)>=5,f"{len(media)} media files"))
        checks.append(check_record('word_qr_embedded','QR code linking to the public GitHub repository' in document_xml))
        checks.append(check_record('word_package_no_generation_branding',not any(package_hits.values()),package_hits))
        checks.append(check_record('word_no_custom_properties','docProps/custom.xml' not in package_names))
        checks.append(check_record('word_no_comment_reviewer_metadata',not review_parts and '<w:comment' not in document_xml,review_parts))
    probe=json.loads((ROOT/'qa/workbook_build.json').read_text())
    checks.append(check_record('excel_recalculation_probe',probe['formula_recalculation_probe']=='PASS'))
    workbook_text='\n'.join(str(v) for cells in book['sheets'].values() for v in cells.values() if v is not None)
    checks.append(check_record('excel_no_legacy_equity_proxy_label',not re.search(r'Tier\s*1\s*proxy|EVE\s*/\s*Tier',workbook_text,re.I)))
    return checks


if __name__ == '__main__':
    try:
        result=acceptance(require_render=True)
    except Exception as exc:
        from .render_report import WordRenderError
        if isinstance(exc,WordRenderError):
            raise SystemExit(f"WORD_RENDER_FAIL: {exc}") from exc
        raise
    failed=[check for check in result if check['status']!='PASS']
    print(json.dumps({'status':'FAIL' if failed else 'PASS','checks':len(result),'failed':failed},indent=2))
    if failed:
        raise SystemExit(1)
