import pandas as pd
from pathlib import Path
from src.analysis.disproportionality import DisproportionalityAnalyzer
from src.cleaning.data_cleaner import FAERSDataCleaner
from src.visualization.charts import generate_all_charts
import yaml

print("Loading cleaned processed data...")
demographics_df = pd.read_csv("data/processed/demographics.csv")
reactions_df = pd.read_csv("data/processed/reactions.csv")
outcomes_df = pd.read_csv("data/processed/outcomes.csv")

with open("config/drug_classes.yaml", "r") as f:
    config = yaml.safe_load(f)

cleaner = FAERSDataCleaner()
analyzer = DisproportionalityAnalyzer(
    ror_threshold=1.0,
    prr_threshold=2.0,
    chi_sq_threshold=4.0,
    min_count=3
)

total_cohort_reports = demographics_df["safetyreportid"].nunique()
print(f"Total study cohort reports: {total_cohort_reports:,}")

cleaned_data = {
    "demographics": demographics_df,
    "reactions": reactions_df,
    "outcomes": outcomes_df
}

drug_event_pairs = []

for drug_def in config["drug_class"]["drugs"]:
    generic = drug_def["generic_name"]
    drug_report_ids = set(
        demographics_df[demographics_df["drug_queried"] == generic]["safetyreportid"].unique()
    )
    total_drug_reports = len(drug_report_ids)

    if total_drug_reports == 0:
        continue

    print(f"Processing: {generic} ({total_drug_reports:,} reports)")

    for event_def in config["adverse_events"]:
        event_name = event_def["name"]
        meddra_pts = event_def["meddra_pts"]
        category = event_def.get("category", "Unknown")

        contingency = cleaner.build_contingency_table(
            reactions_df=reactions_df,
            target_drug_reports=drug_report_ids,
            target_event_terms=meddra_pts,
            total_reports_in_db=total_cohort_reports,
            total_drug_reports=total_drug_reports,
        )

        drug_event_pairs.append({
            "drug": generic,
            "event": event_name,
            "event_category": category,
            "contingency": contingency,
        })

results_df = analyzer.run_analysis(drug_event_pairs)

# Save updated results
results_path = Path("data/processed/signal_results.csv")
results_df.to_csv(results_path, index=False)
print(f"Saved: {results_path}")

signals_df = analyzer.get_signal_summary(results_df)
if not signals_df.empty:
    signals_path = Path("data/processed/signals_detected.csv")
    signals_df.to_csv(signals_path, index=False)
    print(f"Saved signals: {signals_path}")

# Regenerate all charts
generate_all_charts(
    results_df=results_df,
    reactions_df=reactions_df,
    demographics_df=demographics_df,
    outcomes_df=outcomes_df,
)

print("ALL DONE SUCCESSFULLY!")
