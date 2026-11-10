"""Small terminal smoke test for the included demo dataset."""
from pathlib import Path
from analytics import AnalyticsEngine, SEGMENT_ORDER

BASE_DIR = Path(__file__).resolve().parent
engine = AnalyticsEngine(BASE_DIR / "online_retail_sample.csv", "Smoke test demo dataset").run()

assert engine.summary["customers"] >= 4, "Expected at least four customers."
assert engine.summary["orders"] > 0, "Expected valid orders."
assert len(engine.cleaned) > 0, "Expected cleaned transaction rows."
assert set(engine.customers["Segment"].astype(str)).issubset(set(SEGMENT_ORDER)), "Unexpected segment label."

customer_id = str(engine.customers.iloc[0]["CustomerID"])
recommendations = engine.recommendation_payload(customer_id)
assert recommendations["customer"]["customerId"] == customer_id
assert "recommendations" in recommendations

expected_outputs = [
    "cleaned_transactions.csv", "customer_segments.csv", "segment_profiles.csv",
    "segment_scatter.png", "segment_mix.png", "elbow_curve.png"
]
missing = [name for name in expected_outputs if not (BASE_DIR / name).exists()]
assert not missing, f"Missing generated output(s): {', '.join(missing)}"

print("SMOKE TEST PASSED")
print(f"Customers: {engine.summary['customers']} | Orders: {engine.summary['orders']} | Clean rows: {len(engine.cleaned)}")
print(f"Segments: {', '.join(sorted(set(engine.customers['Segment'].astype(str))))}")
print(f"Recommendation check: customer {customer_id} -> {len(recommendations['recommendations'])} product suggestions")
