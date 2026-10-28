from .source_validation import validate_sources
validate_sources()
"""Publication figures from the exact reconciled output tables, no manual numbers."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from .config import ROOT

plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,
                     "axes.spines.right":False,"axes.titleweight":"bold","axes.labelcolor":"#253647",
                     "figure.facecolor":"white","savefig.facecolor":"white","axes.grid":False})
NAVY="#16324f"; TEAL="#167d8d"; RED="#b54741"; GREY="#8799aa"


def save(fig,name):
    fig.tight_layout(pad=1.2)
    fig.savefig(ROOT/f"outputs/figures/{name}.png",dpi=220,bbox_inches="tight")
    plt.close(fig)


def build():
    gap=pd.read_csv(ROOT/"outputs/tables/repricing_gap.csv")
    n=pd.read_csv(ROOT/"outputs/tables/nii_scenarios.csv")
    e=pd.read_csv(ROOT/"outputs/tables/eve_scenarios.csv")
    l=pd.read_csv(ROOT/"outputs/tables/liquidity_daily.csv")
    cal=pd.read_csv(ROOT/"outputs/tables/h8_balance_sheet_calibration.csv")
    fig,ax=plt.subplots(figsize=(8.6,3.0))
    x=np.arange(7)
    ax.bar(x-.19,gap.rsa[:7]/1e6,.38,label="Rate-sensitive assets",color=TEAL)
    ax.bar(x+.19,gap.rsl[:7]/1e6,.38,label="Rate-sensitive liabilities",color=NAVY)
    ax.set_xticks(x,["0–1m","1–3m","3–6m","6–12m","1–2y","2–5y",">5y"])
    ax.set_ylabel("USD million"); ax.legend(frameon=False,loc="upper right",fontsize=9)
    save(fig,"repricing_gap")
    labels=[s.replace("Parallel ","").replace(" bps","") for s in n.scenario[1:]]
    for table,col,name in [(n,"delta_nii","nii_sensitivity"),(e,"delta_eve","eve_sensitivity")]:
        fig,ax=plt.subplots(figsize=(8.6,3.0))
        values=table[col].iloc[1:].to_numpy()/1e6
        ax.barh(labels[::-1],values[::-1],color=[RED if v<0 else TEAL for v in values[::-1]])
        ax.axvline(0,color=GREY,lw=.8); ax.set_xlabel("Change from Base (USD million)")
        save(fig,name)
    fig,ax=plt.subplots(figsize=(8.6,3.1))
    for (name,p),color in zip(l.groupby("scenario",sort=False),[TEAL,GREY,RED]):
        ax.plot(p.day,p.cumulative_liquidity_gap/1e6,label=name,color=color,lw=2)
    ax.axhline(0,color=NAVY,lw=.8); ax.set_xlabel("Days after 23 October 2026")
    ax.set_ylabel("Available cash after stress\nUSD million"); ax.legend(frameon=False,fontsize=9)
    save(fig,"liquidity_survival")
    lineage=json.loads((ROOT/"data/processed/public_data_lineage.json").read_text())
    nodes=pd.read_csv(ROOT/"data/raw/treasury_curve.csv")
    fig,ax=plt.subplots(figsize=(8.6,2.8))
    ax.plot(nodes.tenor_years,nodes.par_rate*100,marker="o",color=NAVY,lw=1.8)
    ax.set_xlabel("Maturity (years)");ax.set_ylabel("Official par yield (%)")
    ax.set_title(f"US Treasury observation {lineage['treasury']['curve_date']}",fontsize=11,loc="left")
    save(fig,"treasury_curve")
    fig,axes=plt.subplots(1,2,figsize=(8.6,3.0))
    for ax,side,title in zip(axes,["asset","funding"],["Assets","Funding and residual"]):
        part=cal.loc[cal.side.eq(side)]
        names=part.group.str.replace("_"," ").str.replace("residual equity proxy","Residual proxy")
        ax.barh(names.iloc[::-1],part.synthetic_pct_total_assets.iloc[::-1]*100,color=NAVY)
        ax.set_xlabel("Share of total assets (%)");ax.set_title(title,fontsize=11)
    save(fig,"balance_calibration")


if __name__=="__main__": build()
