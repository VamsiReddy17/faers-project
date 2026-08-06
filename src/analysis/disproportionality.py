"""
Disproportionality Analysis Engine

Computes Reporting Odds Ratio (ROR) and Proportional Reporting Ratio (PRR)
for drug-event pairs from FAERS 2x2 contingency tables.
"""

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class SignalResult:
    """Result of a disproportionality analysis for one drug-event pair."""

    drug: str
    event: str
    event_category: str
    a: int  # Drug + Event
    b: int  # Drug + No Event
    c: int  # No Drug + Event
    d: int  # No Drug + No Event
    ror: float
    ror_lower_ci: float
    ror_upper_ci: float
    prr: float
    chi_squared: float
    is_signal_ror: bool
    is_signal_prr: bool

    def to_dict(self) -> dict:
        return {
            "drug": self.drug,
            "event": self.event,
            "event_category": self.event_category,
            "a (drug+event)": self.a,
            "b (drug+no_event)": self.b,
            "c (no_drug+event)": self.c,
            "d (no_drug+no_event)": self.d,
            "ROR": round(self.ror, 3),
            "ROR_lower_CI": round(self.ror_lower_ci, 3),
            "ROR_upper_CI": round(self.ror_upper_ci, 3),
            "PRR": round(self.prr, 3),
            "Chi_squared": round(self.chi_squared, 3),
            "Signal_ROR": self.is_signal_ror,
            "Signal_PRR": self.is_signal_prr,
            "Signal": self.is_signal_ror or self.is_signal_prr,
        }


class DisproportionalityAnalyzer:
    """
    Computes ROR and PRR with confidence intervals for FAERS data.

    Signal thresholds (configurable):
    - ROR: Lower bound of 95% CI > 1
    - PRR: PRR >= 2 AND Chi² >= 4 AND a >= 3
    """

    def __init__(
        self,
        ror_threshold: float = 1.0,
        prr_threshold: float = 2.0,
        chi_sq_threshold: float = 4.0,
        min_count: int = 3,
    ):
        """
        Initialize analyzer with signal detection thresholds.

        Args:
            ror_threshold: Minimum lower 95% CI for ROR signal.
            prr_threshold: Minimum PRR value for PRR signal.
            chi_sq_threshold: Minimum chi-squared for PRR signal.
            min_count: Minimum count of 'a' cell for any signal.
        """
        self.ror_threshold = ror_threshold
        self.prr_threshold = prr_threshold
        self.chi_sq_threshold = chi_sq_threshold
        self.min_count = min_count

    def compute_ror(self, a: int, b: int, c: int, d: int) -> tuple[float, float, float]:
        """
        Compute Reporting Odds Ratio with 95% confidence interval.

        ROR = (a * d) / (b * c)
        95% CI = exp(ln(ROR) ± 1.96 * sqrt(1/a + 1/b + 1/c + 1/d))

        Args:
            a: Drug+Event count
            b: Drug+NoEvent count
            c: NoDrug+Event count
            d: NoDrug+NoEvent count

        Returns:
            Tuple of (ROR, lower_CI, upper_CI). Returns (0, 0, 0) if
            computation is not possible (zero cells).
        """
        # Apply 0.5 continuity correction if any cell is zero
        if any(x == 0 for x in [a, b, c, d]):
            a_adj, b_adj, c_adj, d_adj = a + 0.5, b + 0.5, c + 0.5, d + 0.5
        else:
            a_adj, b_adj, c_adj, d_adj = a, b, c, d

        try:
            ror = (a_adj * d_adj) / (b_adj * c_adj)
            ln_ror = math.log(ror)
            se = math.sqrt(1 / a_adj + 1 / b_adj + 1 / c_adj + 1 / d_adj)
            lower = math.exp(ln_ror - 1.96 * se)
            upper = math.exp(ln_ror + 1.96 * se)
            return (round(ror, 4), round(lower, 4), round(upper, 4))
        except (ValueError, ZeroDivisionError):
            return (0.0, 0.0, 0.0)

    def compute_prr(self, a: int, b: int, c: int, d: int) -> tuple[float, float]:
        """
        Compute Proportional Reporting Ratio and Chi-squared.

        PRR = (a / (a + b)) / (c / (c + d))
        Chi² = Σ((O - E)² / E) for all cells

        Returns:
            Tuple of (PRR, chi_squared).
        """
        try:
            prop_drug = a / (a + b) if (a + b) > 0 else 0
            prop_other = c / (c + d) if (c + d) > 0 else 0
            prr = prop_drug / prop_other if prop_other > 0 else 0.0

            # Chi-squared with Yates' correction
            n = a + b + c + d
            if n == 0:
                return (0.0, 0.0)

            # Expected values for 2x2 table
            row1 = a + b
            row2 = c + d
            col1 = a + c
            col2 = b + d

            e_a = (row1 * col1) / n if n > 0 else 0
            e_b = (row1 * col2) / n if n > 0 else 0
            e_c = (row2 * col1) / n if n > 0 else 0
            e_d = (row2 * col2) / n if n > 0 else 0

            chi_sq = 0.0
            for observed, expected in [(a, e_a), (b, e_b), (c, e_c), (d, e_d)]:
                if expected > 0:
                    chi_sq += ((observed - expected) ** 2) / expected

            return (round(prr, 4), round(chi_sq, 4))
        except ZeroDivisionError:
            return (0.0, 0.0)

    def analyze_pair(
        self,
        drug: str,
        event: str,
        event_category: str,
        contingency: dict[str, int],
    ) -> SignalResult:
        """
        Run full disproportionality analysis for one drug-event pair.

        Args:
            drug: Drug generic name.
            event: Adverse event name.
            event_category: Category (e.g., "Metabolic", "CNS").
            contingency: Dict with keys 'a', 'b', 'c', 'd'.

        Returns:
            SignalResult with all computed measures and signal flags.
        """
        a, b, c, d = contingency["a"], contingency["b"], contingency["c"], contingency["d"]

        ror, ror_lower, ror_upper = self.compute_ror(a, b, c, d)
        prr, chi_sq = self.compute_prr(a, b, c, d)

        # Signal detection
        is_signal_ror = (
            a >= self.min_count
            and ror_lower > self.ror_threshold
        )
        is_signal_prr = (
            a >= self.min_count
            and prr >= self.prr_threshold
            and chi_sq >= self.chi_sq_threshold
        )

        return SignalResult(
            drug=drug,
            event=event,
            event_category=event_category,
            a=a,
            b=b,
            c=c,
            d=d,
            ror=ror,
            ror_lower_ci=ror_lower,
            ror_upper_ci=ror_upper,
            prr=prr,
            chi_squared=chi_sq,
            is_signal_ror=is_signal_ror,
            is_signal_prr=is_signal_prr,
        )

    def run_analysis(
        self,
        drug_event_contingencies: list[dict],
    ) -> pd.DataFrame:
        """
        Run disproportionality analysis for all drug-event pairs.

        Args:
            drug_event_contingencies: List of dicts, each with:
                - drug: str
                - event: str
                - event_category: str
                - contingency: dict with a, b, c, d

        Returns:
            DataFrame with all results, sorted by ROR descending.
        """
        results = []
        for item in drug_event_contingencies:
            result = self.analyze_pair(
                drug=item["drug"],
                event=item["event"],
                event_category=item["event_category"],
                contingency=item["contingency"],
            )
            results.append(result.to_dict())

        df = pd.DataFrame(results)

        if not df.empty:
            df = df.sort_values("ROR", ascending=False).reset_index(drop=True)

        # Summary stats
        total_pairs = len(df)
        signal_count = df["Signal"].sum() if "Signal" in df.columns else 0
        print(f"\n  Analysis complete: {total_pairs} drug-event pairs evaluated")
        print(f"  Signals detected: {signal_count}")

        return df

    def get_signal_summary(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """Filter results to only statistically significant signals."""
        if results_df.empty:
            return results_df
        return (
            results_df[results_df["Signal"] == True]
            .sort_values("ROR", ascending=False)
            .reset_index(drop=True)
        )
