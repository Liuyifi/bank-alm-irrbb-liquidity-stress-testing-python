"""English nine-page Word report from reviewed metrics and official lineage."""
import json
from datetime import datetime, timezone
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from .config import ROOT

OUTPUT=ROOT/"report/Banking_Book_Interest_Rate_and_Liquidity_Stress_Testing_Report.docx"


def million(v,dec=3): return f"{v/1e6:,.{dec}f}"
def percent(v): return f"{v*100:,.1f}%"
def signed(v,dec=3): return f"{v/1e6:+,.{dec}f}"


def build():
    from .source_validation import validate_sources
    validate_sources()
    d=json.loads((ROOT/"data/processed/artifact_payload.json").read_text());m=d["metrics"];line=d["lineage"]
    doc=Document();sec=doc.sections[0]
    sec.page_width=Inches(8.27);sec.page_height=Inches(11.69)
    sec.top_margin=Inches(.66);sec.bottom_margin=Inches(.62);sec.left_margin=Inches(.72);sec.right_margin=Inches(.72)
    sec.header_distance=Inches(.28);sec.footer_distance=Inches(.28)
    styles=doc.styles
    # Remove template accent rules inherited by Title/Subtitle in bundled defaults.
    for style in styles:
        for border in style.element.xpath('.//w:pBdr'):
            border.getparent().remove(border)
    for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption']:
        styles[name].font.name='Arial';styles[name].font.color.rgb=RGBColor(0,0,0)
    normal=styles['Normal'];normal.font.size=Pt(10.5);normal.paragraph_format.space_after=Pt(7);normal.paragraph_format.line_spacing=1.10
    styles['Title'].font.size=Pt(24);styles['Title'].font.bold=True
    styles['Title'].paragraph_format.space_after=Pt(10)
    styles['Heading 1'].font.size=Pt(17);styles['Heading 1'].paragraph_format.space_after=Pt(9)
    styles['Heading 2'].font.size=Pt(11.5);styles['Heading 2'].font.bold=True
    styles['Heading 2'].paragraph_format.space_before=Pt(9);styles['Heading 2'].paragraph_format.space_after=Pt(5)
    styles['Caption'].font.size=Pt(9);styles['Caption'].paragraph_format.space_after=Pt(7)
    header=sec.header.paragraphs[0];header.text='TREASURY RISK ANALYTICS     |     STYLIZED BANKING BOOK'
    header.runs[0].font.size=Pt(8);header.runs[0].font.color.rgb=RGBColor(0,0,0)
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run('23 October 2026     |     ')
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    for r in footer.runs:r.font.size=Pt(8)
    doc.core_properties.title='Banking Book Interest Rate and Liquidity Stress Testing'
    doc.core_properties.subject='Independent public-data-anchored synthetic ALM and liquidity portfolio project'
    doc.core_properties.author='Portfolio Research'
    doc.core_properties.last_modified_by='Portfolio Research'
    doc.core_properties.created=datetime(2026,10,23,tzinfo=timezone.utc)
    doc.core_properties.modified=datetime(2026,10,23,tzinfo=timezone.utc)

    def p(text,style=None): return doc.add_paragraph(text,style)
    def h(text):doc.add_heading(text,level=2)
    def page(title):doc.add_page_break();doc.add_heading(title,level=1)
    def table(headers,rows,widths=None,fontsize=9.3):
        t=doc.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
        if widths:
            for col,w in zip(t.columns,widths):col.width=Inches(w)
        for c,text in zip(t.rows[0].cells,headers):c.text=str(text)
        for row in rows:
            for c,text in zip(t.add_row().cells,row):c.text=str(text)
        for i,row in enumerate(t.rows):
            pr=row._tr.get_or_add_trPr();keep=OxmlElement('w:cantSplit');pr.append(keep)
            if i==0:
                repeat=OxmlElement('w:tblHeader');pr.append(repeat)
            for j,c in enumerate(row.cells):
                if widths:c.width=Inches(widths[j])
                c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                tcPr=c._tc.get_or_add_tcPr()
                borders=OxmlElement('w:tcBorders')
                for side in ['top','left','bottom','right']:
                    e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
                tcPr.append(borders)
                shd=OxmlElement('w:shd');shd.set(qn('w:fill'),'16324F' if i==0 else ('EFF3F7' if i%2==0 else 'FFFFFF'));tcPr.append(shd)
                margins=OxmlElement('w:tcMar')
                for side in ['top','bottom','left','right']:
                    e=OxmlElement('w:'+side);e.set(qn('w:w'),'65');e.set(qn('w:type'),'dxa');margins.append(e)
                tcPr.append(margins)
                for par in c.paragraphs:
                    par.paragraph_format.space_after=Pt(0);par.paragraph_format.line_spacing=1.06
                    par.alignment=WD_ALIGN_PARAGRAPH.LEFT if j==0 else WD_ALIGN_PARAGRAPH.CENTER
                    for run in par.runs:
                        run.font.size=Pt(fontsize);run.font.bold=i==0;run.font.color.rgb=RGBColor(255,255,255) if i==0 else RGBColor(0,0,0)
        doc.add_paragraph().paragraph_format.space_after=Pt(0)
        return t
    def fig(name,caption,width=6.6):
        par=doc.add_paragraph();par.paragraph_format.space_after=Pt(2)
        run=par.add_run();run.add_picture(str(ROOT/f'outputs/figures/{name}.png'),width=Inches(width))
        # Native accessibility description in the drawing.
        pr=run._r.xpath('.//wp:docPr')[0];pr.set('descr',caption)
        p(caption,'Caption')

    doc.add_paragraph('Banking Book Interest Rate and Liquidity Stress Testing','Title')
    p('Public data anchored synthetic portfolio study for Treasury Risk and ALM', 'Subtitle')
    doc.add_heading('Executive Summary',level=1)
    p(f"The book is more exposed to changes in long-term economic value than to the first year of interest income. "
      f"A parallel increase of 200 basis points reduces EVE by USD {million(abs(m['worst_delta_eve']))} million "
      f"and 12-month NII by USD {abs(m['worst_delta_nii'])/1000:,.1f} thousand. Treasury review should prioritize fixed-rate asset duration and the stability of deposit behavior.")
    table(['Measure','Base or adverse result'],[
        ['Total assets and records',f"USD {million(m['total_assets'],1)}m across {m['positions']} synthetic records"],
        ['Base 12-month NII',f"USD {million(m['base_nii'])}m"],
        ['Worst Delta NII',f"USD {signed(m['worst_delta_nii'])}m  ({percent(m['worst_delta_nii_pct'])})"],
        ['Base EVE',f"USD {million(m['base_eve'])}m"],
        ['Worst Delta EVE',f"USD {signed(m['worst_delta_eve'])}m  ({percent(m['worst_delta_eve_equity_proxy_pct'])} of stylized equity proxy)"],
        ['Combined liquidity result',f"No breach in 90 days; USD {million(d['liquidity_scenarios'][2]['remaining_liquidity_buffer'])}m terminal buffer"]
    ],[3.0,3.8],10)
    p('The modest default NII decline depends on assumed deposit pass-through. Setting all non-maturity deposit betas to 15% changes the +200 bps NII result to a gain, while a 55% beta produces a larger loss. The default projection therefore provides a scenario result, not a reliable forecast of realized earnings.')
    p('Combined stress consumes almost all available liquidity over the tested horizon. A survival statement of at least 90 days is justified; a longer survival estimate is not. The analysis should support review of deposit retention assumptions, liquid-asset eligibility and the timing of monetization before any limit or hedging decision.')
    h('Scope and evidence')
    p(f"Official Treasury par yields observed on {line['treasury']['curve_date']} anchor market rates. Federal Reserve H.8 released on {line['h8']['release_date']}, with observations for {line['h8']['observation_date']}, anchors industry balance-sheet shares. All {m['positions']} contract/group records remain synthetic. This is an independent portfolio project, with internal illustrative shocks and liquidity proxies. It has not been deployed or approved for regulatory use.")

    page('Balance Sheet and Assumptions')
    p('The observed H.8 all-commercial-bank balance sheet is scaled to USD 100 million of assets. Category shares are preserved to within 0.01 percentage point. No single bank is represented. The public residual share supplies the H.8 residual-based equity proxy. It is not regulatory capital.')
    table(['Side','Synthetic product','USD m','Records'],[
        [r['side'].title(),r['product'],million(r['principal']),r['positions']] for r in d['balance_sheet']
    ],[.7,3.65,1.2,1.25],9.1)
    h('Observed inputs and modeled fields')
    p('Observed inputs are Treasury par yields and H.8 cash, securities, gross loans, deposits, borrowings, other liabilities, net due to foreign offices and residual balances. H.8 is not seasonally adjusted. XML levels in USD millions are converted to USD billions for calibration.')
    p('Model assumptions divide loans 40:25:10 across mortgages, corporate and consumer products, and deposits 55:20 across non-maturity and term products. Broad securities are represented by fixed-rate government proxies. Net other assets include the effect of loan-loss allowances and unmodeled asset categories; other liabilities include net due to foreign offices. Both other categories remain at carrying value and are not treated as liquid resources.')
    p('Remaining maturities, coupons, reset dates, amortization, reference spreads, deposit betas and runoff rates are simulated with seed 20261023. Contract weights are lognormal, normalized to calibrated product totals and rounded to cents. Record counts reflect manageable contract/group detail, not a claim about industry customer counts.')
    h('Behavior and contractual schedules')
    p(f"Mortgages and consumer loans amortize by equal principal. Corporate loans, securities and term funding are bullet instruments. Interest pays monthly on an ACT/365 basis. NMDs have legal demand maturity but a separate 24–60 month equal-principal behavioral runoff for IRRBB, with monthly betas between 15% and 55%. Their principal-weighted average life is {d['nmd_principal_wal_years']:.3f} years; this is not an estimated market duration. Cash has zero modeled yield. These fields are not inferred from H.8.")

    page('Repricing Gap')
    p('Rate-sensitive principal is assigned to the first contractual reset, or final maturity for fixed-rate instruments. Non-maturity deposits reprice monthly and fall in the shortest bucket. Cash, other non-rate-sensitive items and equity are shown separately from RSA and RSL. This stock gap does not allocate every future amortization installment.')
    fig('repricing_gap','Figure 1  Rate-sensitive assets and liabilities by next repricing bucket')
    table(['Bucket','RSA','RSL','Gap','Cumulative','Gap / assets'],[
        [r['bucket'],million(r['rsa'],2),million(r['rsl'],2),million(r['periodic_gap'],2),million(r['cumulative_gap'],2),percent(r['gap_pct_total_assets'])]
        for r in d['repricing_gap']
    ],[2.02,.83,.83,.83,1.13,1.16],9)
    p('Amounts are USD million. Negative short-bucket gaps identify more immediately repricing funding than assets. A low deposit beta can offset part of that exposure, so the gap alone does not determine NII sensitivity. Longer fixed-rate asset cash flows are the principal reason economic-value sensitivity remains material.')
    p('Python and SQL assign buckets independently using exact one-, three-, six-, twelve-, twenty-four- and sixty-month anniversary cutoffs. Balance-sheet totals and each RSA/RSL bucket reconcile to a USD 0.01 tolerance.')

    page('NII Sensitivity')
    p('The 12-month simulation follows the existing book as it runs off. Fixed coupons remain unchanged until maturity. Floating corporate loans retain their current coupons until the scheduled reset and then use the shocked Treasury-implied forward proxy plus spread. Matured principal is not reinvested or replaced, so these results measure a run-off book rather than constant-balance-sheet earnings.')
    fig('nii_sensitivity','Figure 2  Twelve month Delta NII under internal illustrative scenarios')
    table(['Internal scenario','NII USD m','Delta USD m','Delta / Base'],[
        [r['scenario'],million(r['nii']),signed(r['delta_nii']),percent(r['delta_nii_pct'])] for r in d['nii_scenarios']
    ],[2.78,1.25,1.45,1.32],9.5)
    h('Why the default effect is small')
    worst=[r for r in d['product_contributions'] if r['scenario']==m['worst_nii_scenario']]
    corp=next(r for r in worst if r['product']=='Floating-rate corporate loans');nmd=next(r for r in worst if r['product']=='Non-maturity retail deposits')
    p(f"Under +200 bps, floating corporate income contributes USD {signed(corp['delta_nii'])}m while higher NMD expense contributes USD {signed(nmd['delta_nii'])}m. Fixed-rate products have zero Delta NII in the run-off model. The difference is a small net decline, not proof that the book is immunized.")
    p('NMD coupons equal initial coupon plus beta times the change in the one-month forward index, floored at zero. The initial index is frozen from the Base curve so shocks do not cancel. The Base case permits curve-implied future repricing; down shocks become asymmetric when deposit coupon floors bind.')

    page('EVE Sensitivity')
    p('EVE is the discounted value of asset cash flows less liability cash flows, excluding equity as a liability. Future principal and interest are generated over the full modeled remaining life. Floating coupons are reprojected under each stressed curve. NMD principal follows the behavioral maturity schedule rather than the legal demand maturity.')
    fig('eve_sensitivity','Figure 3  Delta EVE under internal illustrative scenarios')
    table(['Internal scenario','Asset PV','Liability PV','EVE','Delta EVE','Delta / equity proxy'],[
        [r['scenario'],million(r['asset_pv'],2),million(r['liability_pv'],2),million(r['eve'],2),signed(r['delta_eve'],2),percent(r['delta_eve_equity_proxy_pct'])] for r in d['eve_scenarios']
    ],[2.17,.92,.97,.82,.94,.98],8.9)
    p(f"Amounts are USD million. The worst tested change is USD {signed(m['worst_delta_eve'])}m under {m['worst_eve_scenario']}, or {percent(m['worst_delta_eve_equity_proxy_pct'])} of the USD {million(m['equity_residual_proxy'])}m H.8 residual-based equity proxy. This ratio is descriptive; it is not a regulatory capital ratio, a BCBS supervisory outlier test, or a capital-adequacy conclusion.")
    h('Curve construction and valuation boundary')
    p('Each scenario shocks observed par nodes before constructing a simplified discount-curve proxy. Short maturities use a simple annual-rate approximation. From six months onward, synthetic semiannual par bonds are bootstrapped on a half-year grid using linearly interpolated par rates. Discount factors interpolate log-linearly between grid points. The model does not calibrate a zero curve from coupon-instrument prices, and this proxy is not an official Treasury zero curve.')
    p('Cash and other non-rate-sensitive categories are carried at book value as time-zero valuation entries. No credit-spread shock, prepayment, embedded option, basis risk, hedge, or endogenous deposit migration is modeled. Monthly coupon conventions approximate securities and funding cash-flow timing.')

    page('Liquidity Stress and Survival Horizon')
    p('A daily 90-day ledger starts with cash and adds realized government-security monetization, recognized contractual loan inflows and stress outflows. Securities are monetized once at their Base EVE value after the scenario haircut. Their subsequent coupons and maturities are excluded, preventing double counting. Other assets contribute no monetization capacity.')
    fig('liquidity_survival','Figure 4  Available cash after stress flows and scheduled monetization')
    table(['Scenario','Capacity','Outflows','Inflows','Peak need','End buffer','Survival'],[
        [r['scenario'],million(r['counterbalancing_capacity'],2),million(r['total_outflow'],2),million(r['recognized_inflow'],2),million(r['peak_funding_need'],2),million(r['remaining_liquidity_buffer'],2),'At least 90d' if r['survival_censored'] else str(r['survival_days'])+'d'] for r in d['liquidity_scenarios']
    ],[1.27,.88,.88,.88,.88,.9,1.11],9)
    p('Amounts are USD million. All scenarios survive the tested window, so none supports an estimate beyond 90 days. Combined terminal cash is the minimum buffer in that scenario. Counterbalancing capacity is potential sale proceeds before realization and a declining stock afterward; it is not added to cash a second time.')
    table(['Assumption','Idiosyncratic','Market wide','Combined'],[
        ['Retail baseline runoff multiplier','2.0x','1.2x','4.0x'],
        ['Term nonrenewal / wholesale loss','50% / 75%','65% / 85%','100% / 100%'],
        ['Commitment draw / total haircut','25% / 5%','40% / 10%','65% / 14%'],
        ['Monetization day / collection rate','2 / 95%','5 / 85%','7 / 80%']
    ],[2.65,1.38,1.38,1.39],9)
    p('Retail runoff is 7.5–12.5% per record before the scenario multiplier, spread across days with normalized exponential weights. The internal daily cap recognizes inflows only up to 75% of the same-day outflow; excess inflows are discarded rather than carried forward. This conservative timing rule is not a regulatory LCR implementation. No NSFR is calculated.')

    page('Management Interpretation')
    p('The same +200 bps shock produces a small first-year earnings decline and a much larger economic-value decline. Treasury management should read both measures together: delayed repricing protects current coupons but leaves long-lived assets exposed to higher discount rates. A large accounting cash balance does not remove valuation risk.')
    table(['Product','Delta NII USD m','Delta EVE USD m'],[
        [r['product'],signed(r['delta_nii']),signed(r['delta_eve'])] for r in worst
    ],[3.75,1.5,1.55],9.3)
    p('Product contributions above reconcile to the +200 bps aggregate. Signs reflect net income and net economic value; a positive liability EVE contribution offsets asset losses. The table is a bridge of modeled results, not a proposed hedge allocation.')
    h('Validate deposit behavior before setting limits')
    variants={r['variant']:r for r in d['nmd_model_sensitivity'] if r['scenario']=='Parallel up 200 bps'}
    p(f"At a uniform 15% NMD beta, +200 bps Delta NII is USD {signed(variants['NMD beta 15%']['delta_nii'])}m; at 55% it is USD {signed(variants['NMD beta 55%']['delta_nii'])}m. Halving behavioral maturities changes Delta EVE to USD {signed(variants['NMD maturity 50%']['delta_eve'])}m, while extending them by 50% changes it to USD {signed(variants['NMD maturity 150%']['delta_eve'])}m. Each comparison uses its own Base valuation. Deposit assumptions can change the earnings direction and materially alter EVE.")
    h('Review liquidity concentration and execution')
    p('Combined stress leaves approximately 1% of total assets in cash at day 90. Review the availability of unencumbered securities, realistic settlement delays and deposit runoff concentration. The current model assumes all government holdings are eligible for sale and excludes other-liability cash calls. Those assumptions require evidence before treating the terminal buffer as usable contingency capacity.')
    p('A next analytical step is to compare duration reduction, additional liquid resources and deposit-retention strategies under validated assumptions. No hedging cost, instrument eligibility or optimization has been modeled, so this report does not select a transaction.')

    page('Limitations and Next Steps')
    h('Public aggregates do not reveal contract risk')
    p('H.8 anchors an industry balance-sheet structure. It does not supply a bank-specific contractual maturity ladder, deposit beta, liquidity eligibility, regulatory capital or account-level behavior. The internal loan and deposit splits and the mapping of broad securities to government proxies simplify the published categories. Gross loans and the residual net-asset adjustment preserve the observed total without constructing a synthetic trading book.')
    h('Interest rate and valuation limitations')
    p('The model excludes mortgage prepayment, consumer early repayment, default, embedded options, derivative hedges, credit-spread changes, basis shocks and dynamic customer migration. Equal-principal amortization is not a standard annuity mortgage schedule. Treasury-implied forwards are a pricing proxy, not SOFR. Cash has zero yield. Other assets and liabilities are rate-insensitive at carrying value, which can understate their actual risk.')
    p('NII uses existing-book runoff rather than a constant or dynamic balance sheet. EVE includes contractual margins and projected floating coupons, so it is not a claim to any regulatory standardized implementation. Par-to-discount construction and monthly payments approximate market conventions. Only seven deterministic internal rate scenarios are tested; no probabilistic loss estimate is produced.')
    h('Liquidity and capital limitations')
    p('The stress framework does not model insurance status, depositor concentration, intraday settlement, collateral encumbrance, central-bank eligibility, reserve requirements, FX mismatches, derivative margin calls, or cash outflows from the other-liability proxy. Retail runoff and commitment draw schedules are imposed. Rolled funding principal is assumed to remain beyond 90 days, with ongoing interest expense. Newly drawn commitments generate no inflows within the window.')
    p('The daily inflow cap, loan collection discounts and asset haircuts are internal assumptions. Available market capacity is unlimited at the haircut price. A no-breach result is censored at 90 days, not evidence of indefinite survival. The H.8 residual is an accounting aggregate used solely as a stylized equity proxy and cannot support a capital-adequacy conclusion or supervisory outlier test.')
    h('Recommended development sequence')
    p('First replace behavior assumptions with a documented estimation and challenge process. Then add contractual instrument payment calendars, prepayment and basis-risk models. Extend liquidity to encumbrance, concentration and collateral channels and test cap conventions. Add hedges and costs only after the unhedged model is reconciled. A production workflow would require independent model validation, governance, controlled data feeds and an approved operating specification.')
    h('Validation completed')
    p(f"The engine passes {m['core_checks_passed']} dataset controls. The full pytest suite includes source-lock attacks, independently expected contract examples, par-bond repricing, discount monotonicity, reset timing, principal conservation, beta sensitivity and liquidity stock accounting. Five Python/SQL controls pass at USD 0.01: balance and repricing are independent recomputations; liquidity, NII and EVE are partial recomputations using shared Python cash flows or discount inputs. These checks establish internal consistency within the stated assumptions; they do not validate the assumptions empirically.")

    page('Technical Appendix')
    p('Pipeline order: mandatory locked-source and observation-lineage validation, H.8 calibration, synthetic positions, shared cash-flow schedules, Python aggregation, DuckDB reconciliation, automated controls, figures and management artifacts. The frozen run is offline-reproducible; refresh is prohibited in the locked release. All figures and report numbers read the saved CSV and JSON outputs.')
    table(['Measure','Implementation'],[
        ['Repricing gap','RSA minus RSL by first reset/fixed maturity; cumulative sum in bucket order'],
        ['NII','Sum of 12-month asset interest less liability interest; Delta = scenario minus Base'],
        ['EVE','Sum of signed discounted full-life principal and interest; equity excluded'],
        ['Liquidity gap','Opening cash + cumulative recognized inflows - outflows + realized monetization'],
        ['Survival','Last fully funded day before first negative daily gap; at least 90 if no breach'],
        ['Shock definition','Parallels +/-100/200 bps; steepener 0.01(1-2 exp(-t/4)); flattener opposite']
    ],[1.35,5.45],8.9)
    h('Official sources and acquisition record')
    p('US Treasury Daily Treasury Par Yield Curve Rates\n'+line['treasury']['source_url'])
    p(f"Observation {line['treasury']['observation_date']}; selected feed updated {line['treasury']['feed_updated_timestamp']}. Publication-date metadata is the Atom entry update date, not an independently observed market-close timestamp.")
    p('Federal Reserve H.8 official downloadable XML\n'+line['h8']['source_url']+'\nOfficial release cross-check '+line['h8']['release_page'])
    p(f"H.8 released {line['h8']['release_date']}; observed {line['h8']['observation_date']}; all US commercial banks, not seasonally adjusted. Downloaded {line['download_time']}. XML source units are USD millions. No fallback source was used.")
    hashes=table(['Frozen source file','SHA256'],[[Path(r['path']).name,r['sha256']] for r in line['files']],[2.65,4.15],7.6)
    for row in hashes.rows[1:]:
        for c in row.cells:
            for par in c.paragraphs:
                par.alignment=WD_ALIGN_PARAGRAPH.LEFT
    p('Field mappings, source sizes and full paths: data/processed/public_data_lineage.json. Contract fields: data/processed/field_dictionary.csv. Reconciliation SQL: sql/. Control evidence: qa/.',style='Caption')
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__=='__main__':build()
