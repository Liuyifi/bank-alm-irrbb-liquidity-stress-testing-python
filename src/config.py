"""All business assumptions are explicit, internal and illustrative."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AS_OF = "2026-10-23"
SEED = 20261023
BUCKETS = ["Overnight to 1 month", "1 to 3 months", "3 to 6 months",
           "6 to 12 months", "1 to 2 years", "2 to 5 years",
           "More than 5 years", "Non-rate-sensitive"]
IR_SCENARIOS = ["Base", "Parallel up 100 bps", "Parallel up 200 bps",
                "Parallel down 100 bps", "Parallel down 200 bps", "Steepener", "Flattener"]
# Number of contracts or explicitly grouped positions, remaining maturity months,
# coupon bounds and amortization. Product totals MUST come from H.8 calibration.
PRODUCTS = {
    "Fixed-rate mortgages": (160, 36, 240, .035, .060, "equal_principal"),
    "Floating-rate corporate loans": (50, 3, 60, .0, .0, "bullet"),
    "Consumer loans": (400, 3, 60, .065, .110, "equal_principal"),
    "Government securities": (12, 6, 120, .025, .055, "bullet"),
    "Cash and liquid assets": (1, 0, 0, 0., 0., "cash"),
    "Non-maturity retail deposits": (220, 24, 60, .005, .015, "behavioral_equal_principal"),
    "Term deposits": (80, 1, 18, .025, .040, "bullet"),
    "Wholesale funding": (12, 1, 12, .030, .045, "bullet"),
    "H.8 residual-based equity proxy": (1, 0, 0, 0., 0., "equity"),
    "Other non-rate-sensitive assets": (1, 0, 0, 0., 0., "carrying_value"),
    "Other non-rate-sensitive liabilities": (1, 0, 0, 0., 0., "carrying_value"),
}
LIQUIDITY = {
    "Idiosyncratic": dict(retail_multiplier=2., term_nonrenewal=.5, wholesale_loss=.75,
                         commitment_draw=.25, extra_haircut=.03, monetization_day=2,
                         collection_rate=.95, frontload=.055),
    "Market-wide": dict(retail_multiplier=1.2, term_nonrenewal=.65, wholesale_loss=.85,
                       commitment_draw=.40, extra_haircut=.08, monetization_day=5,
                       collection_rate=.85, frontload=.025),
    "Combined": dict(retail_multiplier=4., term_nonrenewal=1., wholesale_loss=1.,
                     commitment_draw=.65, extra_haircut=.12, monetization_day=7,
                     collection_rate=.80, frontload=.045),
}
LIQUIDITY_DAYS = 90
INFLOW_CAP = .75  # Internal daily recognized inflow <= 75% of same-day outflows.
CURVE_FLOOR = .0001
