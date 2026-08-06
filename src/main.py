"""
FAERS Pharmacovigilance Signal Mining Pipeline — Main Orchestrator

Runs the full pipeline:
1. Load config
2. Ingest data from openFDA
3. Clean and structure data
4. Run disproportionality analysis (ROR/PRR)
5. Generate visualizations
6. Export results
"""

import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from src.ingestion.openfda_client import OpenFDAClient
from src.cleaning.data_cleaner import FAERSDataCleaner
from src.analysis.disproportionality import DisproportionalityAnalyzer
from src.visualization.charts import generate_all_charts


def load_config(config_path: str = "config/drug_classes.yaml") -> dict:
    """Load drug class configuration from YAML file."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    print(f"✓ Loaded config: {config['study_title']}")
    print(f"  Drug class: {config['drug_class']['name']}")
    print(f"  Drugs: {[d['generic_name'] for d in config['drug_class']['drugs']]}")
    print(f"  Events: {[e['name'] for e in config['adverse_events']]}")
    print(f"  Period: {config['study_period']['start']} – {config['study_period']['end']}")
    return config


def run_ingestion(config: dict) -> dict[str, list]:
    """
    Phase 1: Pull adverse event reports from openFDA for each drug.

    Returns:
        Dict mapping drug name → list of raw report dicts.
    """
    print("\n" + "=" * 60)
    print("PHASE 1: DATA INGESTION")
    print("=" * 60)

    api_config = config.get("api", {})
    client = OpenFDAClient(
        rate_limit_delay=api_config.get("rate_limit_delay_seconds", 0.3),
    )

    start_date = config["study_period"]["start"]
    end_date = config["study_period"]["end"]
    primary_only = config.get("analysis", {}).get("primary_suspect_only", True)

    all_reports = {}
    for drug_def in config["drug_class"]["drugs"]:
        generic = drug_def["generic_name"]
        brands = drug_def.get("brand_names", [])
        all_names = [generic] + brands

        reports = client.fetch_drug_events(
            drug_name=generic,
            drug_names_all=all_names,
            start_date=start_date,
            end_date=end_date,
            primary_suspect_only=primary_only,
            max_records=25000,  # openFDA limit per query set
        )
        all_reports[generic] = reports

    # Also get total database count for denominators
    total_db = client.get_total_reports_count(start_date, end_date)
    all_reports["__total_db_count__"] = total_db

    return all_reports


def run_cleaning(config: dict, all_reports: dict) -> dict[str, pd.DataFrame]:
    """
    Phase 2: Parse, clean, deduplicate, and standardize data.

    Returns:
        Dict of cleaned DataFrames (demographics, drugs, reactions, outcomes).
    """
    print("\n" + "=" * 60)
    print("PHASE 2: DATA CLEANING")
    print("=" * 60)

    cleaner = FAERSDataCleaner()

    # Parse each drug's reports
    all_parsed = []
    for drug_def in config["drug_class"]["drugs"]:
        generic = drug_def["generic_name"]
        reports = all_reports.get(generic, [])
        if reports:
            parsed = cleaner.parse_reports(reports, drug_label=generic)
            all_parsed.append(parsed)

    # Merge all drugs together
    merged = cleaner.merge_all_drugs(all_parsed)

    # Deduplicate demographics (one per report)
    merged["demographics"] = cleaner.deduplicate(merged["demographics"])

    # Standardize demographics
    merged["demographics"] = cleaner.standardize_demographics(merged["demographics"])

    # Save processed data
    cleaner.save_processed_data(merged)

    return merged


def run_analysis(
    config: dict,
    cleaned_data: dict[str, pd.DataFrame],
    total_db_count: int,
) -> pd.DataFrame:
    """
    Phase 3: Compute ROR/PRR for all drug-event combinations.

    Returns:
        DataFrame of signal results.
    """
    print("\n" + "=" * 60)
    print("PHASE 3: DISPROPORTIONALITY ANALYSIS")
    print("=" * 60)

    analysis_config = config.get("analysis", {})
    analyzer = DisproportionalityAnalyzer(
        ror_threshold=analysis_config.get("ror_signal_threshold", 1.0),
        prr_threshold=analysis_config.get("prr_signal_threshold", 2.0),
        chi_sq_threshold=analysis_config.get("chi_squared_threshold", 4.0),
        min_count=analysis_config.get("min_report_count", 3),
    )
    cleaner = FAERSDataCleaner()

    reactions_df = cleaned_data["reactions"]
    demographics_df = cleaned_data["demographics"]

    if demographics_df.empty or reactions_df.empty:
        print("  ⚠ No data available for analysis. Check API ingestion.")
        return pd.DataFrame()

    # Total unique reports in study dataset
    total_cohort_reports = demographics_df["safetyreportid"].nunique()
    print(f"  Total study cohort reports: {total_cohort_reports:,}")

    # Build contingency tables for every drug-event combination
    drug_event_pairs = []

    for drug_def in config["drug_class"]["drugs"]:
        generic = drug_def["generic_name"]

        # Get unique report IDs for this drug
        drug_report_ids = set(
            demographics_df[demographics_df["drug_queried"] == generic][
                "safetyreportid"
            ].unique()
        )
        total_drug_reports = len(drug_report_ids)

        if total_drug_reports == 0:
            print(f"  ⚠ No reports for {generic}, skipping...")
            continue

        print(f"\n  Processing: {generic} ({total_drug_reports:,} reports)")

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

    # Run analysis
    results_df = analyzer.run_analysis(drug_event_pairs)

    # Save results
    results_path = Path("data/processed/signal_results.csv")
    results_df.to_csv(results_path, index=False)
    print(f"\n  Results saved to: {results_path}")

    # Save signals-only
    signals_df = analyzer.get_signal_summary(results_df)
    if not signals_df.empty:
        signals_path = Path("data/processed/signals_detected.csv")
        signals_df.to_csv(signals_path, index=False)
        print(f"  Signals saved to: {signals_path}")

    return results_df


def run_visualization(
    results_df: pd.DataFrame,
    cleaned_data: dict[str, pd.DataFrame],
):
    """Phase 4: Generate all charts and visualizations."""
    generate_all_charts(
        results_df=results_df,
        reactions_df=cleaned_data["reactions"],
        demographics_df=cleaned_data["demographics"],
        outcomes_df=cleaned_data["outcomes"],
    )


def print_summary(results_df: pd.DataFrame):
    """Print a formatted summary of the analysis."""
    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)

    if results_df.empty:
        print("  No results to summarize.")
        return

    total_pairs = len(results_df)
    signal_count = results_df["Signal"].sum()

    print(f"\n  Total drug-event pairs analyzed: {total_pairs}")
    print(f"  Signals detected (ROR or PRR): {signal_count}")
    print(f"  Signal rate: {signal_count/total_pairs*100:.1f}%")

    if signal_count > 0:
        print(f"\n  {'─'*55}")
        print(f"  TOP 10 SIGNALS BY ROR:")
        print(f"  {'─'*55}")

        top_signals = results_df[results_df["Signal"] == True].head(10)
        for _, row in top_signals.iterrows():
            print(
                f"  {row['drug'].capitalize():15s} → {row['event']:30s} "
                f"ROR={row['ROR']:7.2f} "
                f"[{row['ROR_lower_CI']:.2f}–{row['ROR_upper_CI']:.2f}] "
                f"n={row['a (drug+event)']:,}"
            )


def main():
    """Run the complete FAERS pharmacovigilance pipeline."""
    print("╔" + "═" * 58 + "╗")
    print("║  FAERS PHARMACOVIGILANCE SIGNAL MINING PIPELINE          ║")
    print("╚" + "═" * 58 + "╝")

    # Load config
    config = load_config()

    # Phase 1: Ingest
    all_reports = run_ingestion(config)
    total_db_count = all_reports.pop("__total_db_count__", 0)

    # Phase 2: Clean
    cleaned_data = run_cleaning(config, all_reports)

    # Phase 3: Analyze
    results_df = run_analysis(config, cleaned_data, total_db_count)

    # Phase 4: Visualize
    run_visualization(results_df, cleaned_data)

    # Summary
    print_summary(results_df)

    print("\n✓ Pipeline complete! Check 'data/processed/' and 'reports/' for outputs.")


if __name__ == "__main__":
    main()
