"""
Visualization Module for FAERS Pharmacovigilance Analysis

Generates publication-quality charts:
- Forest plots (ROR with 95% CI)
- Bar charts (top ADRs by count)
- Demographics charts (age/sex distribution)
- Time trend plots
- Bubble charts (drug × event heatmaps)
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

# Set global style
sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "font.family": "sans-serif",
})

REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Color palette
DRUG_COLORS = {
    "risperidone": "#E63946",
    "olanzapine": "#457B9D",
    "quetiapine": "#2A9D8F",
    "aripiprazole": "#E9C46A",
    "clozapine": "#F4A261",
}
DEFAULT_PALETTE = list(DRUG_COLORS.values()) + sns.color_palette("husl", 10)


def forest_plot(
    results_df: pd.DataFrame,
    title: str = "Forest Plot — Reporting Odds Ratio (ROR) with 95% CI",
    top_n: int = 20,
    filename: str = "forest_plot.png",
):
    """
    Create a forest plot showing ROR and 95% confidence intervals.

    Args:
        results_df: DataFrame from DisproportionalityAnalyzer.run_analysis()
        title: Plot title.
        top_n: Number of top drug-event pairs to display.
        filename: Output filename.
    """
    df = results_df.head(top_n).copy()
    if df.empty:
        print("  No data for forest plot.")
        return

    df = df.sort_values("ROR", ascending=True).reset_index(drop=True)
    df["label"] = df["drug"].str.capitalize() + " → " + df["event"]

    fig, ax = plt.subplots(figsize=(12, max(6, len(df) * 0.45)))

    y_pos = range(len(df))

    # Plot CI lines
    for i, row in df.iterrows():
        color = "#E63946" if row.get("Signal", False) else "#457B9D"
        ax.plot(
            [row["ROR_lower_CI"], row["ROR_upper_CI"]],
            [i, i],
            color=color,
            linewidth=2,
            solid_capstyle="round",
        )

    # Plot ROR points
    colors = ["#E63946" if s else "#457B9D" for s in df.get("Signal", [False] * len(df))]
    ax.scatter(df["ROR"], y_pos, c=colors, s=80, zorder=5, edgecolors="white", linewidth=0.5)

    # Reference line at ROR=1
    ax.axvline(x=1, color="#888888", linestyle="--", linewidth=1, alpha=0.7, label="ROR = 1 (null)")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(df["label"], fontsize=10)
    ax.set_xlabel("Reporting Odds Ratio (ROR)", fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xscale("log")

    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#E63946", markersize=10, label="Signal detected"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#457B9D", markersize=10, label="No signal"),
        Line2D([0], [0], color="#888888", linestyle="--", label="ROR = 1 (null)"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9)

    plt.tight_layout()
    filepath = REPORT_DIR / filename
    plt.savefig(filepath)
    plt.close()
    print(f"  Saved: {filepath}")


def top_adrs_bar_chart(
    reactions_df: pd.DataFrame,
    title: str = "Top 15 Most Reported Adverse Drug Reactions",
    top_n: int = 15,
    filename: str = "top_adrs.png",
):
    """
    Horizontal bar chart of the most frequently reported ADRs.

    Args:
        reactions_df: DataFrame with 'reaction_meddra_pt' column.
        title: Plot title.
        top_n: Number of top events to show.
        filename: Output filename.
    """
    counts = (
        reactions_df["reaction_meddra_pt"]
        .value_counts()
        .head(top_n)
        .sort_values(ascending=True)
    )

    fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.4)))

    colors = sns.color_palette("viridis", len(counts))
    bars = ax.barh(range(len(counts)), counts.values, color=colors, edgecolor="white", height=0.7)

    ax.set_yticks(range(len(counts)))
    ax.set_yticklabels([t.title() for t in counts.index], fontsize=10)
    ax.set_xlabel("Number of Reports", fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)

    # Add count labels on bars
    for bar, val in zip(bars, counts.values):
        ax.text(
            bar.get_width() + max(counts) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}",
            va="center",
            fontsize=9,
            color="#333333",
        )

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    plt.tight_layout()
    filepath = REPORT_DIR / filename
    plt.savefig(filepath)
    plt.close()
    print(f"  Saved: {filepath}")


def adrs_by_drug_chart(
    reactions_df: pd.DataFrame,
    title: str = "Top ADRs by Drug",
    top_n_events: int = 10,
    filename: str = "adrs_by_drug.png",
):
    """
    Grouped bar chart showing top ADRs broken down by drug.
    """
    # Get top N events overall
    top_events = reactions_df["reaction_meddra_pt"].value_counts().head(top_n_events).index.tolist()

    # Filter and pivot
    filtered = reactions_df[reactions_df["reaction_meddra_pt"].isin(top_events)]
    pivot = filtered.groupby(["reaction_meddra_pt", "drug_queried"]).size().unstack(fill_value=0)
    pivot = pivot.loc[top_events]

    fig, ax = plt.subplots(figsize=(14, 8))

    pivot.plot(
        kind="bar",
        ax=ax,
        width=0.8,
        color=[DRUG_COLORS.get(col, c) for col, c in zip(pivot.columns, DEFAULT_PALETTE)],
        edgecolor="white",
    )

    ax.set_xlabel("Adverse Event (MedDRA PT)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Number of Reports", fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xticklabels([t.title() for t in pivot.index], rotation=45, ha="right", fontsize=9)
    ax.legend(title="Drug", loc="upper right", fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    plt.tight_layout()
    filepath = REPORT_DIR / filename
    plt.savefig(filepath)
    plt.close()
    print(f"  Saved: {filepath}")


def demographics_chart(
    demographics_df: pd.DataFrame,
    filename: str = "demographics.png",
):
    """
    Create a 2-panel demographics chart: age distribution and sex distribution.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # --- Age distribution ---
    ax1 = axes[0]
    if "age_group" in demographics_df.columns:
        age_counts = demographics_df["age_group"].value_counts().sort_index()
        colors_age = sns.color_palette("Blues_d", len(age_counts))
        bars = ax1.bar(range(len(age_counts)), age_counts.values, color=colors_age, edgecolor="white")
        ax1.set_xticks(range(len(age_counts)))
        ax1.set_xticklabels(age_counts.index.astype(str), fontsize=10)

        for bar, val in zip(bars, age_counts.values):
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(age_counts) * 0.01,
                f"{val:,}",
                ha="center",
                fontsize=9,
            )
    ax1.set_xlabel("Age Group", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Number of Reports", fontsize=12, fontweight="bold")
    ax1.set_title("Age Distribution of Reports", fontsize=13, fontweight="bold")

    # --- Sex distribution ---
    ax2 = axes[1]
    if "sex_label" in demographics_df.columns:
        sex_counts = demographics_df["sex_label"].value_counts()
        sex_colors = {"Male": "#457B9D", "Female": "#E63946", "Unknown": "#AAAAAA"}
        colors_sex = [sex_colors.get(s, "#888888") for s in sex_counts.index]

        wedges, texts, autotexts = ax2.pie(
            sex_counts.values,
            labels=sex_counts.index,
            colors=colors_sex,
            autopct="%1.1f%%",
            startangle=90,
            pctdistance=0.85,
            wedgeprops=dict(width=0.4, edgecolor="white"),
        )
        for text in autotexts:
            text.set_fontsize(10)
            text.set_fontweight("bold")
    ax2.set_title("Sex Distribution of Reports", fontsize=13, fontweight="bold")

    plt.suptitle("Patient Demographics", fontsize=15, fontweight="bold", y=1.02)
    plt.tight_layout()
    filepath = REPORT_DIR / filename
    plt.savefig(filepath)
    plt.close()
    print(f"  Saved: {filepath}")


def time_trend_chart(
    demographics_df: pd.DataFrame,
    title: str = "Adverse Event Reports Over Time by Drug",
    filename: str = "time_trends.png",
):
    """
    Line chart showing report counts per quarter for each drug.
    """
    if "receive_quarter" not in demographics_df.columns:
        print("  No time data available for trend chart.")
        return

    quarterly = (
        demographics_df.groupby(["receive_quarter", "drug_queried"])
        .size()
        .unstack(fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(14, 7))

    for i, drug in enumerate(quarterly.columns):
        color = DRUG_COLORS.get(drug, DEFAULT_PALETTE[i % len(DEFAULT_PALETTE)])
        ax.plot(
            range(len(quarterly)),
            quarterly[drug],
            marker="o",
            markersize=4,
            linewidth=2,
            color=color,
            label=drug.capitalize(),
        )

    ax.set_xticks(range(len(quarterly)))
    ax.set_xticklabels(quarterly.index.astype(str), rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("Quarter", fontsize=12, fontweight="bold")
    ax.set_ylabel("Number of Reports", fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.legend(title="Drug", loc="upper left", fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    plt.tight_layout()
    filepath = REPORT_DIR / filename
    plt.savefig(filepath)
    plt.close()
    print(f"  Saved: {filepath}")


def outcomes_heatmap(
    outcomes_df: pd.DataFrame,
    title: str = "Serious Outcomes by Drug",
    filename: str = "outcomes_heatmap.png",
):
    """
    Heatmap showing serious outcome counts per drug.
    """
    outcome_cols = ["death", "hospitalization", "life_threatening", "disability"]
    available_cols = [c for c in outcome_cols if c in outcomes_df.columns]

    if not available_cols or "drug_queried" not in outcomes_df.columns:
        print("  Insufficient data for outcomes heatmap.")
        return

    # Convert to numeric
    for col in available_cols:
        outcomes_df[col] = pd.to_numeric(outcomes_df[col], errors="coerce").fillna(0)

    pivot = outcomes_df.groupby("drug_queried")[available_cols].sum()
    pivot.columns = [c.replace("_", " ").title() for c in pivot.columns]
    pivot.index = [i.capitalize() for i in pivot.index]

    fig, ax = plt.subplots(figsize=(10, max(5, len(pivot) * 0.8)))

    sns.heatmap(
        pivot,
        annot=True,
        fmt=",.0f",
        cmap="YlOrRd",
        linewidths=0.5,
        linecolor="white",
        ax=ax,
        cbar_kws={"label": "Number of Reports"},
    )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Outcome Type", fontsize=12, fontweight="bold")
    ax.set_ylabel("Drug", fontsize=12, fontweight="bold")

    plt.tight_layout()
    filepath = REPORT_DIR / filename
    plt.savefig(filepath)
    plt.close()
    print(f"  Saved: {filepath}")


def signal_bubble_chart(
    results_df: pd.DataFrame,
    title: str = "Signal Landscape — Drug × Adverse Event",
    filename: str = "signal_bubble.png",
):
    """
    Bubble chart: x = drug, y = event, size = report count, color = ROR.
    """
    df = results_df.copy()
    if df.empty:
        print("  No data for bubble chart.")
        return

    # Create numeric positions
    drugs = df["drug"].unique().tolist()
    events = df["event"].unique().tolist()
    df["drug_pos"] = df["drug"].map({d: i for i, d in enumerate(drugs)})
    df["event_pos"] = df["event"].map({e: i for i, e in enumerate(events)})

    fig, ax = plt.subplots(figsize=(max(10, len(drugs) * 2), max(8, len(events) * 0.6)))

    # Size based on report count (a cell)
    sizes = df["a (drug+event)"].values
    size_scale = 1000 / max(sizes) if max(sizes) > 0 else 1
    plot_sizes = sizes * size_scale + 50

    scatter = ax.scatter(
        df["drug_pos"],
        df["event_pos"],
        s=plot_sizes,
        c=np.log1p(df["ROR"]),
        cmap="YlOrRd",
        alpha=0.8,
        edgecolors="white",
        linewidth=1,
    )

    # Mark signals with a ring
    signals = df[df.get("Signal", False) == True]
    if not signals.empty:
        signal_sizes = signals["a (drug+event)"].values * size_scale + 50
        ax.scatter(
            signals["drug_pos"],
            signals["event_pos"],
            s=signal_sizes + 80,
            facecolors="none",
            edgecolors="#E63946",
            linewidth=2,
            label="Signal detected",
        )

    ax.set_xticks(range(len(drugs)))
    ax.set_xticklabels([d.capitalize() for d in drugs], fontsize=11, fontweight="bold")
    ax.set_yticks(range(len(events)))
    ax.set_yticklabels(events, fontsize=10)
    ax.set_xlabel("Drug", fontsize=12, fontweight="bold")
    ax.set_ylabel("Adverse Event", fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)

    cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
    cbar.set_label("log(1 + ROR)", fontsize=10)

    if not signals.empty:
        ax.legend(loc="upper right", fontsize=10)

    plt.tight_layout()
    filepath = REPORT_DIR / filename
    plt.savefig(filepath)
    plt.close()
    print(f"  Saved: {filepath}")


def generate_all_charts(
    results_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    demographics_df: pd.DataFrame,
    outcomes_df: pd.DataFrame,
):
    """Generate all visualization charts."""
    print("\n" + "=" * 60)
    print("GENERATING VISUALIZATIONS")
    print("=" * 60)

    forest_plot(results_df)
    top_adrs_bar_chart(reactions_df)
    adrs_by_drug_chart(reactions_df)
    demographics_chart(demographics_df)
    time_trend_chart(demographics_df)
    outcomes_heatmap(outcomes_df)
    signal_bubble_chart(results_df)

    print(f"\n  All charts saved to: {REPORT_DIR.absolute()}")
