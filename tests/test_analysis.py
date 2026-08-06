"""
Unit Tests for Disproportionality Analysis

Tests ROR and PRR computation against known values,
edge cases (zero cells), and signal detection logic.
"""

import math
import unittest

from src.analysis.disproportionality import DisproportionalityAnalyzer, SignalResult


class TestRORComputation(unittest.TestCase):
    """Test Reporting Odds Ratio calculations."""

    def setUp(self):
        self.analyzer = DisproportionalityAnalyzer()

    def test_basic_ror(self):
        """Test ROR with known 2x2 table values."""
        # Example: a=50, b=450, c=100, d=9400
        # ROR = (50 * 9400) / (450 * 100) = 470000 / 45000 ≈ 10.44
        ror, lower, upper = self.analyzer.compute_ror(50, 450, 100, 9400)
        self.assertAlmostEqual(ror, 10.4444, places=2)
        self.assertGreater(lower, 1.0)  # Should be a signal
        self.assertGreater(upper, ror)
        self.assertLess(lower, ror)

    def test_ror_no_signal(self):
        """Test ROR where there's no disproportionate reporting."""
        # Proportional reporting: same rate for drug vs others
        # a=10, b=990, c=100, d=9900
        # ROR = (10*9900)/(990*100) = 99000/99000 = 1.0
        ror, lower, upper = self.analyzer.compute_ror(10, 990, 100, 9900)
        self.assertAlmostEqual(ror, 1.0, places=1)

    def test_ror_zero_cell_continuity_correction(self):
        """Test that zero cells get continuity correction (0.5 added)."""
        ror, lower, upper = self.analyzer.compute_ror(0, 500, 100, 9400)
        self.assertGreater(ror, 0)  # Should not be zero or NaN
        self.assertEqual(lower >= 0, True)

    def test_ror_confidence_interval_width(self):
        """Larger sample → narrower CI."""
        _, lower_small, upper_small = self.analyzer.compute_ror(5, 95, 50, 9850)
        _, lower_large, upper_large = self.analyzer.compute_ror(50, 950, 500, 98500)
        ci_width_small = upper_small - lower_small
        ci_width_large = upper_large - lower_large
        # Relative width should be smaller for larger sample
        self.assertGreater(
            ci_width_small / (upper_small + lower_small),
            ci_width_large / (upper_large + lower_large),
        )


class TestPRRComputation(unittest.TestCase):
    """Test Proportional Reporting Ratio calculations."""

    def setUp(self):
        self.analyzer = DisproportionalityAnalyzer()

    def test_basic_prr(self):
        """Test PRR with known values."""
        # a=50, b=450, c=100, d=9400
        # PRR = (50/500) / (100/9500) = 0.1 / 0.01053 ≈ 9.5
        prr, chi_sq = self.analyzer.compute_prr(50, 450, 100, 9400)
        self.assertGreater(prr, 2.0)  # Should be a signal
        self.assertGreater(chi_sq, 4.0)

    def test_prr_no_signal(self):
        """Test PRR where reporting is proportional."""
        # a=10, b=990, c=100, d=9900
        prr, chi_sq = self.analyzer.compute_prr(10, 990, 100, 9900)
        self.assertAlmostEqual(prr, 1.0, places=1)

    def test_prr_zero_denominator(self):
        """Test PRR when no non-drug events exist."""
        prr, chi_sq = self.analyzer.compute_prr(10, 90, 0, 0)
        self.assertEqual(prr, 0.0)


class TestSignalDetection(unittest.TestCase):
    """Test signal threshold logic."""

    def setUp(self):
        self.analyzer = DisproportionalityAnalyzer(
            ror_threshold=1.0,
            prr_threshold=2.0,
            chi_sq_threshold=4.0,
            min_count=3,
        )

    def test_strong_signal_detected(self):
        """Strong signal: high ROR, high PRR, sufficient count."""
        result = self.analyzer.analyze_pair(
            drug="test_drug",
            event="test_event",
            event_category="test",
            contingency={"a": 50, "b": 450, "c": 100, "d": 9400},
        )
        self.assertTrue(result.is_signal_ror)
        self.assertTrue(result.is_signal_prr)

    def test_no_signal_proportional(self):
        """No signal when reporting is proportional."""
        result = self.analyzer.analyze_pair(
            drug="test_drug",
            event="test_event",
            event_category="test",
            contingency={"a": 10, "b": 990, "c": 100, "d": 9900},
        )
        self.assertFalse(result.is_signal_ror)
        self.assertFalse(result.is_signal_prr)

    def test_minimum_count_threshold(self):
        """Signal should not fire if count < min_count."""
        result = self.analyzer.analyze_pair(
            drug="test_drug",
            event="test_event",
            event_category="test",
            contingency={"a": 2, "b": 10, "c": 5, "d": 10000},
        )
        # Even if ROR is high, a=2 < min_count=3 → no signal
        self.assertFalse(result.is_signal_ror)
        self.assertFalse(result.is_signal_prr)

    def test_result_to_dict(self):
        """Test that SignalResult serializes correctly."""
        result = self.analyzer.analyze_pair(
            drug="risperidone",
            event="Weight Gain",
            event_category="Metabolic",
            contingency={"a": 100, "b": 900, "c": 200, "d": 8800},
        )
        d = result.to_dict()
        self.assertIn("drug", d)
        self.assertIn("ROR", d)
        self.assertIn("Signal", d)
        self.assertEqual(d["drug"], "risperidone")


class TestAnalyzerBatch(unittest.TestCase):
    """Test batch analysis across multiple drug-event pairs."""

    def test_run_analysis_returns_sorted_df(self):
        analyzer = DisproportionalityAnalyzer()
        pairs = [
            {
                "drug": "drug_a",
                "event": "event_1",
                "event_category": "cat",
                "contingency": {"a": 10, "b": 90, "c": 50, "d": 9850},
            },
            {
                "drug": "drug_b",
                "event": "event_2",
                "event_category": "cat",
                "contingency": {"a": 50, "b": 450, "c": 100, "d": 9400},
            },
        ]
        results_df = analyzer.run_analysis(pairs)
        self.assertEqual(len(results_df), 2)
        # Should be sorted by ROR descending
        self.assertGreaterEqual(
            results_df.iloc[0]["ROR"], results_df.iloc[1]["ROR"]
        )


if __name__ == "__main__":
    unittest.main()
