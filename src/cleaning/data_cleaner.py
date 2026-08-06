"""
Data Cleaner for FAERS Adverse Event Reports

Handles parsing raw openFDA JSON responses into structured DataFrames,
deduplication, drug name standardization, and contingency table construction.
"""

import pandas as pd
import numpy as np
from typing import Optional


class FAERSDataCleaner:
    """Cleans and structures raw FAERS data from openFDA API responses."""

    def __init__(self):
        """Initialize the data cleaner."""
        self.demographics_df = None
        self.drugs_df = None
        self.reactions_df = None
        self.outcomes_df = None

    def parse_reports(self, reports: list[dict], drug_label: str) -> dict[str, pd.DataFrame]:
        """
        Parse a list of raw FAERS report dicts into structured DataFrames.

        Args:
            reports: List of report dicts from openFDA API.
            drug_label: Label for the drug (e.g., generic name) to tag records.

        Returns:
            Dict with keys 'demographics', 'drugs', 'reactions', 'outcomes'.
        """
        demographics = []
        drugs = []
        reactions = []
        outcomes = []

        for report in reports:
            report_id = report.get("safetyreportid", "")
            case_id = report.get("safetyreportversion", "")
            receive_date = report.get("receivedate", "")
            country = report.get("occurcountry", "Unknown")
            serious = report.get("serious", "")
            primary_source = report.get("primarysource") or {}
            reporter_type = primary_source.get("qualification", "Unknown")

            # --- Demographics ---
            patient = report.get("patient") or {}
            age = None
            age_unit = None
            if "patientonsetage" in patient:
                age = patient.get("patientonsetage")
                age_unit = patient.get("patientonsetageunit", "801")  # 801 = years
            sex = patient.get("patientsex", "0")  # 0=Unknown, 1=Male, 2=Female
            weight = patient.get("patientweight")

            demographics.append({
                "safetyreportid": report_id,
                "case_version": case_id,
                "receive_date": receive_date,
                "country": country,
                "age": age,
                "age_unit": age_unit,
                "sex": sex,
                "weight": weight,
                "serious": serious,
                "reporter_type": reporter_type,
                "drug_queried": drug_label,
            })

            # --- Drugs ---
            for drug_entry in (patient.get("drug") or []):
                generic_name = ""
                brand_name = drug_entry.get("medicinalproduct", "")
                openfda = drug_entry.get("openfda") or {}
                if openfda:
                    generic_names = openfda.get("generic_name") or []
                    generic_name = generic_names[0] if generic_names else ""

                drugs.append({
                    "safetyreportid": report_id,
                    "drug_queried": drug_label,
                    "medicinal_product": brand_name,
                    "generic_name": generic_name.lower(),
                    "drug_characterization": drug_entry.get("drugcharacterization", ""),
                    "drug_indication": drug_entry.get("drugindication", ""),
                    "route": drug_entry.get("drugadministrationroute", ""),
                    "dose": drug_entry.get("drugstructuredosagenumb", ""),
                    "dose_unit": drug_entry.get("drugstructuredosageunit", ""),
                })

            # --- Reactions ---
            for reaction in (patient.get("reaction") or []):
                reactions.append({
                    "safetyreportid": report_id,
                    "drug_queried": drug_label,
                    "reaction_meddra_pt": reaction.get(
                        "reactionmeddrapt", ""
                    ).lower(),
                    "reaction_outcome": reaction.get("reactionoutcome", ""),
                })

            # --- Outcomes ---
            seriousness_fields = {
                "death": report.get("seriousnessdeath", ""),
                "hospitalization": report.get("seriousnesshospitalization", ""),
                "life_threatening": report.get("seriousnesslifethreatening", ""),
                "disability": report.get("seriousnessdisabling", ""),
                "congenital_anomaly": report.get("seriousnesscongenitalanomali", ""),
                "other": report.get("seriousnessother", ""),
            }
            outcomes.append({
                "safetyreportid": report_id,
                "drug_queried": drug_label,
                **seriousness_fields,
            })

        result = {
            "demographics": pd.DataFrame(demographics),
            "drugs": pd.DataFrame(drugs),
            "reactions": pd.DataFrame(reactions),
            "outcomes": pd.DataFrame(outcomes),
        }

        print(f"  Parsed {drug_label}: {len(demographics):,} reports, "
              f"{len(drugs):,} drug entries, {len(reactions):,} reactions")

        return result

    def deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate reports. FAERS can contain multiple versions
        of the same case; we keep the latest version.

        Args:
            df: DataFrame with 'safetyreportid' and 'case_version' columns.

        Returns:
            Deduplicated DataFrame.
        """
        before_count = len(df)

        if "case_version" in df.columns:
            # Convert version to numeric for sorting, keep highest
            df["case_version_num"] = pd.to_numeric(
                df["case_version"], errors="coerce"
            ).fillna(0)
            df = df.sort_values("case_version_num", ascending=False)
            df = df.drop_duplicates(subset=["safetyreportid"], keep="first")
            df = df.drop(columns=["case_version_num"])
        else:
            df = df.drop_duplicates(subset=["safetyreportid"], keep="first")

        after_count = len(df)
        removed = before_count - after_count
        print(f"  Deduplication: {before_count:,} → {after_count:,} "
              f"(removed {removed:,} duplicates)")

        return df.reset_index(drop=True)

    def standardize_demographics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and standardize demographic fields.

        - Convert age to years
        - Map sex codes to labels
        - Parse dates
        - Map reporter types
        """
        if df.empty:
            # Add expected columns so downstream code doesn't break
            for col in ["age_years", "age_group", "sex_label", "reporter_label",
                        "receive_date_parsed", "receive_year", "receive_quarter"]:
                df[col] = pd.Series(dtype="object")
            return df

        df = df.copy()

        # --- Age: convert to years ---
        if "age" in df.columns and "age_unit" in df.columns:
            df["age"] = pd.to_numeric(df["age"], errors="coerce")
            # age_unit: 800=decade, 801=year, 802=month, 803=week, 804=day, 805=hour
            age_multiplier = {
                "800": 10,
                "801": 1,
                "802": 1 / 12,
                "803": 1 / 52,
                "804": 1 / 365,
                "805": 1 / 8760,
            }
            df["age_years"] = df.apply(
                lambda row: (
                    row["age"] * age_multiplier.get(str(row["age_unit"]), 1)
                    if pd.notna(row["age"])
                    else np.nan
                ),
                axis=1,
            )
        else:
            df["age_years"] = np.nan

        # --- Age group bins ---
        bins = [0, 17, 29, 44, 64, 120]
        labels = ["0-17", "18-29", "30-44", "45-64", "65+"]
        df["age_group"] = pd.cut(
            df["age_years"], bins=bins, labels=labels, right=True
        )

        # --- Sex mapping ---
        sex_map = {"0": "Unknown", "1": "Male", "2": "Female"}
        df["sex_label"] = df["sex"].astype(str).map(sex_map).fillna("Unknown")

        # --- Reporter type ---
        reporter_map = {
            "1": "Physician",
            "2": "Pharmacist",
            "3": "Other Health Professional",
            "4": "Lawyer",
            "5": "Consumer/Non-Health Professional",
        }
        df["reporter_label"] = (
            df["reporter_type"].astype(str).map(reporter_map).fillna("Unknown")
        )

        # --- Parse dates ---
        df["receive_date_parsed"] = pd.to_datetime(
            df["receive_date"], format="%Y%m%d", errors="coerce"
        )
        df["receive_year"] = df["receive_date_parsed"].dt.year
        df["receive_quarter"] = df["receive_date_parsed"].dt.to_period("Q").astype(str)

        return df

    def merge_all_drugs(
        self, all_parsed_data: list[dict[str, pd.DataFrame]]
    ) -> dict[str, pd.DataFrame]:
        """
        Merge parsed data from multiple drugs into combined DataFrames.

        Args:
            all_parsed_data: List of dicts from parse_reports(), one per drug.

        Returns:
            Dict with merged DataFrames for all tables.
        """
        merged = {}
        for table_name in ["demographics", "drugs", "reactions", "outcomes"]:
            frames = [d[table_name] for d in all_parsed_data if len(d[table_name]) > 0]
            if frames:
                merged[table_name] = pd.concat(frames, ignore_index=True)
            else:
                merged[table_name] = pd.DataFrame()

        print(f"\n  Merged totals:")
        for name, df in merged.items():
            print(f"    {name}: {len(df):,} rows")

        return merged

    def build_contingency_table(
        self,
        reactions_df: pd.DataFrame,
        target_drug_reports: set,
        target_event_terms: list[str],
        total_reports_in_db: int,
        total_drug_reports: int,
    ) -> dict:
        """
        Build a 2x2 contingency table for a drug-event pair.

        Args:
            reactions_df: DataFrame of all reactions.
            target_drug_reports: Set of safetyreportids for the target drug.
            target_event_terms: List of MedDRA PTs for the target event.
            total_reports_in_db: Total reports in FAERS for the period.
            total_drug_reports: Total reports for the target drug.

        Returns:
            Dict with keys 'a', 'b', 'c', 'd' for the 2x2 table.
        """
        # Normalize event terms for matching
        target_terms_lower = [t.lower() for t in target_event_terms]

        # Reports with target drug AND target event
        drug_event_reports = reactions_df[
            (reactions_df["safetyreportid"].isin(target_drug_reports))
            & (reactions_df["reaction_meddra_pt"].isin(target_terms_lower))
        ]["safetyreportid"].nunique()

        a = drug_event_reports
        b = total_drug_reports - a

        # Reports with target event but NOT target drug
        all_event_reports = reactions_df[
            reactions_df["reaction_meddra_pt"].isin(target_terms_lower)
        ]["safetyreportid"].nunique()
        c = all_event_reports - a

        # Reports with neither
        d = total_reports_in_db - a - b - c

        return {"a": a, "b": b, "c": c, "d": d}

    def save_processed_data(
        self, data: dict[str, pd.DataFrame], output_dir: str = "data/processed"
    ):
        """Save all processed DataFrames to CSV files."""
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for name, df in data.items():
            filepath = output_path / f"{name}.csv"
            df.to_csv(filepath, index=False)
            print(f"  Saved {name}: {len(df):,} rows → {filepath}")
