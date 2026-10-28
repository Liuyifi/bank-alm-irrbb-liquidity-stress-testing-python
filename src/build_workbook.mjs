import fs from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
execFileSync(process.env.ALM_PYTHON || 'python3', ['-m','src.source_validation'], {cwd:root,stdio:'inherit'});
const data=JSON.parse(await fs.readFile(path.join(root,'data/processed/artifact_payload.json'),'utf8'));
const wb=Workbook.create();
const names=['Executive Summary','Assumptions','Balance Sheet','Repricing Gap','NII Scenarios','EVE Scenarios',
             'Liquidity Stress','Daily Liquidity','Product Contributions','Position Ledger','Public Inputs','Data Quality'];
const sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const navy='#16324F',teal='#167D8D',grey='#EAF0F5',black='#182B3A',blue='#1556A3',green='#146C43';
const num='#,##0.000;(#,##0.000);"-"';
const pct='0.0%;(0.0%);"-"';
const col=i=>{let s='';for(let n=i;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};

function base(name,title,note,last='J',rows=45){
 const s=sheets[name];s.showGridLines=false;s.tabColor=name==='Assumptions'?teal:name==='Data Quality'?'#8799AA':navy;
 s.getRange(`A1:${last}${rows}`).format.font={name:'Arial',size:11,color:black};
 s.getRange('A:B').format.columnWidth=2.4;
 s.getRange(`C1:${last}${rows}`).format.rowHeight=23;
 s.mergeCells(`C2:${last}3`);s.getRange('C2').values=[[title]];
 s.getRange('C2').format.font={name:'Arial',size:20,bold:true,color:navy};
 s.mergeCells(`C4:${last}4`);s.getRange('C4').values=[[note]];
 s.getRange('C4').format.font={name:'Arial',size:10,color:'#4A6070'};s.getRange('C4').format.wrapText=true;s.getRange('C4').format.rowHeight=34;
 s.freezePanes.freezeRows(6);s.freezePanes.freezeColumns(3);
 return s;
}

function table(s,headers,rows,{start=6,widths=[],formats={},name='Table',fontSize=11}={}){
 const endCol=col(headers.length+2),end=start+rows.length;
 s.getRange(`C${start}:${endCol}${end}`).values=[headers,...rows];
 const t=s.tables.add(`C${start}:${endCol}${end}`,true,name);t.showFilterButton=true;
 s.getRange(`C${start}:${endCol}${end}`).format.font={name:'Arial',size:fontSize,color:black};
 s.getRange(`C${start}:${endCol}${end}`).format.borders={preset:'all',style:'thin',color:'#D9E2EA'};
 s.getRange(`C${start}:${endCol}${start}`).format={fill:navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:36};
 rows.forEach((_,i)=>{if(i%2===1)s.getRange(`C${start+i+1}:${endCol}${start+i+1}`).format.fill=grey;});
 widths.forEach((w,i)=>s.getRange(`${col(i+3)}:${col(i+3)}`).format.columnWidth=w);
 for(const [i,format] of Object.entries(formats))s.getRange(`${col(Number(i)+3)}${start+1}:${col(Number(i)+3)}${end}`).setNumberFormat(format);
 return {start,end,endCol};
}

function chart(s,title,category,value,anchor1='C18',anchor2='J32',type='bar'){
 const c=s.charts.add(type,[s.getRange(category),s.getRange(value)]);c.title=title;c.setPosition(anchor1,anchor2);
 c.hasLegend=false;c.titleTextStyle.fontSize=14;c.titleTextStyle.typeface='Arial';
 c.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:11}};
 c.yAxis={numberFormatCode:'0.0',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:11}};
 c.yAxis.title.text='USD million';
 if(c.series.items[0])c.series.items[0].fill=teal;
 return c;
}

// Output snapshot with live arithmetic and references, not an editable risk engine.
const ex=base('Executive Summary','Bank Treasury Risk Management Pack','23 October 2026 | Synthetic USD banking book calibrated to official H.8 shares','J',35);
table(ex,['Metric','Value','Units','Interpretation'],[
 ['Total assets',0,'USD million','H.8 category shares scaled to USD 100m'],
 ['Position records',data.metrics.positions,'Contracts / groups','Synthetic, deterministic seed 20261023'],
 ['Base 12-month NII',0,'USD million','Existing book runoff; no replacement'],
 ['Worst Delta NII',0,'USD million',data.metrics.worst_nii_scenario],
 ['Base EVE',0,'USD million','Assets less liabilities; equity excluded'],
 ['Worst Delta EVE',0,'USD million',data.metrics.worst_eve_scenario],
 ['Delta EVE / stylized equity proxy',0,'Percent','H.8 residual-based proxy; not a BCBS outlier test'],
 ['Combined survival lower bound',90,'Days','No breach within tested 90-day window'],
 ['Combined terminal buffer',0,'USD million','After scheduled asset monetization'],
 ['Combined peak funding need',0,'USD million','Maximum negative available cash over horizon']
],{name:'ExecutiveMetrics',widths:[34,21,23,61],formats:{1:num}});
ex.getRange('C7:C16').format.wrapText=true;ex.getRange('C7:F16').format.rowHeight=32;
ex.getRange('D7').formulas=[["=SUMIF('Balance Sheet'!C7:C17,\"asset\",'Balance Sheet'!F7:F17)"]];
ex.getRange('D9:D13').formulas=[["='NII Scenarios'!D7"],["=MIN('NII Scenarios'!E7:E13)"],["='EVE Scenarios'!F7"],["=MIN('EVE Scenarios'!G7:G13)"],["=MIN('EVE Scenarios'!H7:H13)"]];
ex.getRange('D13').setNumberFormat(pct);ex.getRange('D8').setNumberFormat('#,##0');ex.getRange('D14').setNumberFormat('0');
ex.getRange('D15:D16').formulas=[["='Liquidity Stress'!I9"],["='Liquidity Stress'!H9"]];
ex.mergeCells('C20:J22');ex.getRange('C20').values=[['EVE is materially sensitive to higher rates while the default NII effect is small. Deposit beta sensitivity reverses the NII direction. Combined stress retains a limited buffer after 90 days.']];
ex.getRange('C20').format={wrapText:true,font:{name:'Arial',size:12,color:navy},fill:grey};
ex.mergeCells('C25:J27');ex.getRange('C25').values=[['Read-only management outputs. Refresh by rerunning the Python engine and artifact builders. Rate scenarios are internal illustrations. Liquidity results are internal survival proxies, with no formal LCR or NSFR calculation.']];ex.getRange('C25').format.wrapText=true;

const ass=base('Assumptions','Assumptions and refresh scope','Blue values are documented inputs. This workbook presents frozen Python engine outputs.','F',50);
table(ass,['Parameter','Setting','Classification','Definition'],data.assumptions,{name:'ModelAssumptions',widths:[34,32,25,79],fontSize:10});
ass.getRange('D7:D31').format.font={name:'Arial',size:10,color:blue};ass.getRange('C7:F31').format.wrapText=true;ass.getRange('C7:F31').format.rowHeight=36;
data.assumptions.forEach((r,i)=>{if(['Cash yield','Recognized inflow cap','Government eligibility','Government base haircut'].includes(r[0]))ass.getRange(`D${i+7}`).setNumberFormat('0.0%');if(r[0]==='Portfolio scale')ass.getRange(`D${i+7}`).setNumberFormat('$#,##0');});
table(ass,['Scenario','Retail multiplier','Term nonrenewal','Wholesale loss','Commitment draw','Extra haircut','Monetization day','Collection rate'],data.liquidity_assumptions.map(r=>[r.scenario,r.retail_multiplier,r.term_nonrenewal,r.wholesale_loss,r.commitment_draw,r.extra_haircut,r.monetization_day,r.collection_rate]),{start:35,name:'LiquidityAssumptions',formats:{2:pct,3:pct,4:pct,5:pct,7:pct}});
ass.getRange('G:J').format.columnWidth=22;

const bal=base('Balance Sheet','Calibrated balance sheet','All amounts USD million. Coupons are model assumptions. H.8 is an industry aggregate.','J',40);
table(bal,['Side','Product','Records','Principal USD m','Weighted coupon'],data.balance_sheet.map(r=>[r.side,r.product,r.positions,r.principal/1e6,r.weighted_coupon]),{name:'BalanceSheet',widths:[14,43,13,20,21],formats:{3:num,4:pct}});
table(bal,['Public category','Target share','Synthetic USD m','Synthetic share','Difference pp'],data.h8_balance_sheet_calibration.map(r=>[({cash_assets:'Cash assets',securities:'Securities',loans:'Loans',other_assets_net:'Other net assets',deposits:'Deposits',borrowings:'Borrowings',other_liabilities_net:'Other net liabilities',residual_equity_proxy:'Residual equity proxy'})[r.group],r.target_pct_total_assets,r.synthetic_usd/1e6,r.synthetic_pct_total_assets,r.difference_pct_points]),{start:22,name:'H8Calibration',formats:{1:pct,2:num,3:pct,4:'0.000000'}});

bal.getRange('C:C').format.columnWidth=29;
bal.getRange('C23:C30').format.wrapText=true;bal.getRange('C23:G30').format.rowHeight=32;
bal.getRange('D7:D17').format.wrapText=true;bal.getRange('C7:G17').format.rowHeight=32;

const gap=base('Repricing Gap','Repricing gap','Whole principal assigned at first reset or fixed maturity. USD million; gap percentage denominator is total assets.','J',36);
table(gap,['Bucket','RSA USD m','RSL USD m','Gap USD m','Cumulative USD m','Gap / assets'],data.repricing_gap.map(r=>[r.bucket,r.rsa/1e6,r.rsl/1e6,0,0,0]),{name:'RepricingGap',widths:[30,18,18,18,22,19],formats:{1:num,2:num,3:num,4:num,5:pct}});
for(let r=7;r<=14;r++)gap.getRange(`F${r}:H${r}`).formulas=[[`=D${r}-E${r}`,`=SUM($F$7:F${r})`,`=F${r}/'Executive Summary'!$D$7`]];
gap.getRange('L6:M13').values=[['Bucket','Gap'],...['0-1m','1-3m','3-6m','6-12m','1-2y','2-5y','>5y'].map(x=>[x,0])];
for(let r=7;r<=13;r++)gap.getRange(`M${r}`).formulas=[[`=F${r}`]];
chart(gap,'Periodic repricing gap','L6:L13','M6:M13','C19','J33');

const nii=base('NII Scenarios','Twelve month NII sensitivity','USD million. Base is a curve-implied projection with contractual coupons and modeled deposit behavior.','J',35);
table(nii,['Internal scenario','NII USD m','Delta NII USD m','Delta NII / Base'],data.nii_scenarios.map(r=>[r.scenario,r.nii/1e6,0,0]),{name:'NIIScenarios',widths:[34,22,24,24],formats:{1:num,2:num,3:pct}});
for(let r=7;r<=13;r++)nii.getRange(`E${r}:F${r}`).formulas=[[`=D${r}-$D$7`,`=E${r}/$D$7`]];
nii.getRange('L6:M13').values=[['Scenario','Delta NII'],...['Base','+100','+200','-100','-200','Steepener','Flattener'].map(x=>[x,0])];
for(let r=7;r<=13;r++)nii.getRange(`M${r}`).formulas=[[`=E${r}`]];
const nc=chart(nii,'Delta NII by internal scenario','L6:L13','M6:M13');
nc.yAxis={numberFormatCode:'0.000',numberFormatSourceLinked:false};

const eve=base('EVE Scenarios','Economic value sensitivity','USD million. The H.8 residual-based equity proxy is not regulatory capital.','J',35);
table(eve,['Internal scenario','Asset PV USD m','Liability PV USD m','EVE USD m','Delta EVE USD m','Delta / stylized equity proxy'],data.eve_scenarios.map(r=>[r.scenario,r.asset_pv/1e6,r.liability_pv/1e6,0,0,0]),{name:'EVEScenarios',widths:[34,21,22,20,23,30],formats:{1:num,2:num,3:num,4:num,5:pct}});
const equityRow=data.balance_sheet.findIndex(r=>r.side==='equity')+7;
for(let r=7;r<=13;r++)eve.getRange(`F${r}:H${r}`).formulas=[[`=D${r}-E${r}`,`=F${r}-$F$7`,`=G${r}/'Balance Sheet'!$F$${equityRow}`]];
eve.getRange('C6:H6').format.rowHeight=48;
eve.getRange('L6:M13').values=[['Scenario','Delta EVE'],...['Base','+100','+200','-100','-200','Steepener','Flattener'].map(x=>[x,0])];
for(let r=7;r<=13;r++)eve.getRange(`M${r}`).formulas=[[`=G${r}`]];
chart(eve,'Delta EVE by internal scenario','L6:L13','M6:M13');

const liq=base('Liquidity Stress','Liquidity stress and survival','USD million. Survival is censored at 90 days when no breach occurs. Daily 75% inflow cap is an internal rule.','J',35);
table(liq,['Scenario','Opening cash','Capacity after haircut','Outflows','Recognized inflow','Peak need','Terminal buffer','Survival days','Censored'],data.liquidity_scenarios.map(r=>[r.scenario,r.opening_cash/1e6,r.counterbalancing_capacity/1e6,r.total_outflow/1e6,r.recognized_inflow/1e6,r.peak_funding_need/1e6,r.remaining_liquidity_buffer/1e6,r.survival_days,r.survival_censored]),{name:'LiquidityScenarios',widths:[22,18,25,18,23,18,23,20,17],formats:{1:num,2:num,3:num,4:num,5:num,6:num,7:'0'}});
const helper=[['Day',...data.liquidity_scenarios.map(r=>r.scenario)]];
for(let d=1;d<=90;d++)helper.push([d,...data.liquidity_scenarios.map(s=>data.liquidity_daily.find(r=>r.scenario===s.scenario&&r.day===d).cumulative_liquidity_gap/1e6)]);
liq.getRange('M6:P96').values=helper;liq.getRange('N7:P96').setNumberFormat(num);
const lc=liq.charts.add('line',liq.getRange('M6:P96'));lc.title='Available cash after liquidity stress';lc.setPosition('C16','J31');lc.titleTextStyle.typeface='Arial';lc.titleTextStyle.fontSize=14;lc.legend={position:'bottom',textStyle:{typeface:'Arial',fontSize:12}};lc.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:10}};lc.yAxis={numberFormatCode:'0.0',numberFormatSourceLinked:false};lc.yAxis.title.text='USD million';
lc.xAxis={tickLabelInterval:15};
lc.series.items.forEach((s,i)=>{s.line={fill:['#167D8D','#8799AA','#B54741'][i],style:'solid',width:2};});

const daily=base('Daily Liquidity','Daily liquidity ledger','USD million. Capacity is a remaining stock; monetization is a one-time cash inflow.','Q',285);
table(daily,['Scenario','Day','Date','Opening cash effect','Outflow','Recognized inflow','Net cash flow','Monetization','Cumulative net','Liquidity gap','Remaining capacity','Funding need'],data.liquidity_daily.map(r=>[r.scenario,r.day,new Date(r.date+'T00:00:00Z'),0,r.total_outflow/1e6,r.recognized_inflow/1e6,r.net_cash_flow/1e6,r.asset_monetization/1e6,r.cumulative_net_cash_flow/1e6,r.cumulative_liquidity_gap/1e6,r.remaining_counterbalancing_capacity/1e6,r.funding_need/1e6]),{name:'DailyLiquidity',widths:[22,10,17,24,18,22,19,22,22,23,25,22],formats:{2:'yyyy-mm-dd',3:num,4:num,5:num,6:num,7:num,8:num,9:num,10:num,11:num}});
for(let i=0;i<data.liquidity_daily.length;i++){const r=i+7;const source=data.liquidity_daily[i];const open=data.liquidity_scenarios.find(x=>x.scenario===source.scenario).opening_cash/1e6;daily.getRange(`F${r}`).values=[[open]];}

const prod=base('Product Contributions','Product contributions','Signed USD million. Liability interest expense and PV contributions are negative.','K',90);
table(prod,['Scenario','Product','NII USD m','Signed EVE USD m','Delta NII USD m','Delta EVE USD m'],data.product_contributions.map(r=>[r.scenario,r.product,r.nii/1e6,r.signed_eve/1e6,r.delta_nii/1e6,r.delta_eve/1e6]),{name:'ProductContributions',widths:[32,43,20,23,23,23],formats:{2:num,3:num,4:num,5:num},fontSize:10});

const pos=base('Position Ledger','Synthetic position ledger','All records are synthetic contracts or groups. Public H.8 data calibrate category totals only. Principal in USD.','L',950);
const fields=Object.keys(data.positions[0]);
const dateFields=new Set(['origination_date','contractual_maturity','next_repricing_date','behavioral_maturity']);
const matrix=data.positions.map(p=>fields.map(f=>dateFields.has(f)?new Date(p[f]+'T00:00:00Z'):p[f]));
table(pos,fields,matrix,{name:'PositionLedger',widths:fields.map(f=>f==='product'?43:f.includes('date')||dateFields.has(f)?20:22),fontSize:10});
fields.forEach((f,i)=>{const c=col(i+3);if(dateFields.has(f))pos.getRange(`${c}7:${c}944`).setNumberFormat('yyyy-mm-dd');else if(/rate|beta|spread|assumption|haircut/.test(f)&&typeof data.positions[0][f]==='number')pos.getRange(`${c}7:${c}944`).setNumberFormat('0.00%');else if(['principal','undrawn_commitment'].includes(f))pos.getRange(`${c}7:${c}944`).setNumberFormat('#,##0.00;(#,##0.00);"-"');});
pos.getRange(`C6:${col(fields.length+2)}6`).format.rowHeight=58;

const pub=base('Public Inputs','Observed public inputs','Official source snapshots, observed dates and SHA256. Aggregate H.8 shares do not identify a real bank.','I',55);
table(pub,['Treasury date','Maturity years','Par rate'],JSON.parse(await fs.readFile(path.join(root,'data/processed/curve_nodes.json'),'utf8')).map(r=>[new Date(r[0]+'T00:00:00Z'),r[1],r[2]]),{name:'TreasuryNodes',widths:[27,24,24],formats:{0:'yyyy-mm-dd',1:'0.000',2:'0.00%'}});
table(pub,['Source field','Observed USD bn','Observed date','Adjustment'],JSON.parse(await fs.readFile(path.join(root,'data/processed/h8_nodes.json'),'utf8')).map(r=>[r[0],r[1],new Date(r[2]+'T00:00:00Z'),r[3]]),{start:23,name:'H8Observed',widths:[31,25,24,43],formats:{1:'#,##0.000',2:'yyyy-mm-dd'}});
pub.mergeCells('C36:I38');pub.getRange('C36').values=[[`Treasury: ${data.lineage.treasury.source_url}\nH.8: ${data.lineage.h8.source_url}\nDownloaded: ${data.lineage.download_time}`]];pub.getRange('C36').format.wrapText=true;
for(let i=0;i<data.lineage.files.length;i++){let row=41+i*3;pub.mergeCells(`C${row}:I${row+2}`);pub.getRange(`C${row}`).values=[[`${data.lineage.files[i].path}\nSHA256 ${data.lineage.files[i].sha256}`]];pub.getRange(`C${row}`).format={wrapText:true,font:{name:'Arial',size:10,color:blue}};}

const qa=base('Data Quality','Data quality and reconciliation','Engine and official public-source controls. Final document and workbook acceptance evidence is in qa/QA_REPORT.md.','F',42);
table(qa,['Check','Result','Evidence'],data.checks.map(c=>[c.check,c.status,c.detail]),{name:'QualityChecks',widths:[48,14,100],fontSize:10});qa.getRange('C7:E36').format.wrapText=true;qa.getRange('C7:E36').format.rowHeight=34;

wb.recalculate();
// Recalculation proof on a disposable edit; restore before final export.
const before=Number(nii.getRange('D8').values[0][0]);
nii.getRange('D8').values=[[before+.1]];wb.recalculate();
const mutated=Number(nii.getRange('E8').values[0][0]);
if(Math.abs(mutated-((before+.1)-data.metrics.base_nii/1e6))>1e-9)throw new Error('NII delta formula did not recalculate');
nii.getRange('D8').values=[[before]];wb.recalculate();
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},maxChars:4000,summary:'Final formula error scan'});
await fs.writeFile(path.join(root,'qa/workbook_inspection.txt'),errors.ndjson);
const summary=await wb.inspect({kind:'table',range:"'Executive Summary'!C6:F16",include:'values,formulas',tableMaxRows:12,tableMaxCols:5,maxChars:6000});
await fs.writeFile(path.join(root,'qa/workbook_summary_inspection.txt'),summary.ndjson);
const output=await SpreadsheetFile.exportXlsx(wb);await output.save(path.join(root,'outputs/Bank_Treasury_Risk_Management_Pack.xlsx'));
await fs.mkdir(path.join(root,'qa/workbook_previews'),{recursive:true});
for(const [name,range] of Object.entries({'Executive Summary':'C2:J28','Assumptions':'C2:F31','Balance Sheet':'C2:J31','Repricing Gap':'C2:J33','NII Scenarios':'C2:J32','EVE Scenarios':'C2:J32','Liquidity Stress':'C2:K31','Daily Liquidity':'C2:Q18','Product Contributions':'C2:K18','Position Ledger':'C2:L17','Public Inputs':'C2:I33','Data Quality':'C2:F18'})){
 const preview=await wb.render({sheetName:name,range,scale:1.4,format:'png'});
 await fs.writeFile(path.join(root,'qa/workbook_previews',name.replaceAll(' ','_')+'.png'),new Uint8Array(await preview.arrayBuffer()));
}
await fs.writeFile(path.join(root,'qa/workbook_build.json'),JSON.stringify({sheets:names,formula_recalculation_probe:'PASS',export:'PASS',rendered_sheets:names.length},null,2));
console.log('Excel exported, formula probe passed, 12 sheet previews saved.');
