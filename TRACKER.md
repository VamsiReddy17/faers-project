# FAERS Pharmacovigilance Signal Mining — Master Project Tracker

## Project Overview
An end-to-end, config-driven data engineering and signal-mining pipeline for analyzing FDA Adverse Event Reporting System (FAERS) data via openFDA, computing disproportionality metrics (ROR & PRR), generating publication-ready charts, rendering an interactive Streamlit dashboard, and uploading to MotherDuck cloud storage.

---

## 🚦 Project Status Summary

| Status | Phase | Description | Output Artifacts |
| :---: | :--- | :--- | :--- |
| ✅ **COMPLETED** | **Phase 1: Ingestion** | openFDA API client with caching, pagination, and rate-limiting | 5.3 GB raw JSON (`data/raw/`) |
| ✅ **COMPLETED** | **Phase 2: Data Cleaning** | JSON parsing, deduplication, demographic standardization | 4 Clean CSVs (`data/processed/`) |
| ✅ **COMPLETED** | **Phase 3: Signal Mining** | Disproportionality engine computing ROR, PRR, CIs, Chi² | `signal_results.csv`, `signals_detected.csv` |
| ✅ **COMPLETED** | **Phase 4: Visualizations** | 7 publication-quality figures generated in seaborn/matplotlib | 7 PNG charts (`reports/`) |
| ✅ **COMPLETED** | **Phase 5: Dashboard** | Streamlit interactive web application with 5 explorable tabs | `dashboard/app.py` |
| ✅ **COMPLETED** | **Phase 6: Cloud Sync** | Local DuckDB database & MotherDuck cloud export | `data/faers.duckdb`, `md:faers_database` |
| ✅ **COMPLETED** | **Verification** | 12/12 pytest unit tests passing for ROR/PRR math | `tests/test_analysis.py` |

---

## 📈 Current Dataset & Signal Metrics

- **Study Period**: Jan 1, 2018 – Dec 31, 2023
- **Target Drug Class**: Atypical Antipsychotics (Risperidone, Olanzapine, Quetiapine, Aripiprazole, Clozapine)
- **Total Ingested Raw Reports**: 114,000
- **Deduplicated Patient Reports**: **101,708**
- **Total Drug Records**: **953,254**
- **Total Reaction Records**: **484,200**
- **Tested Drug-Event Pairs**: **50**
- **Detected Safety Signals**: **19** *(Signal Rate: 38.0%)*

### Top 5 Detected Signals (by ROR)
1. **Clozapine → Agranulocytosis**: ROR = **10.05** [9.44–10.71], $n=3,700$
2. **Risperidone → Weight Gain**: ROR = **3.62** [3.42–3.83], $n=2,418$
3. **Aripiprazole → Dyslipidaemia**: ROR = **1.99** [1.68–2.37], $n=167$
4. **Aripiprazole → Akathisia**: ROR = **1.95** [1.75–2.17], $n=420$
5. **Olanzapine → QT Prolongation**: ROR = **1.84** [1.66–2.04], $n=537$

---

## 📁 Repository Structure Map

```
Faers Project/
├── .env                                # MotherDuck API token & credentials (git-ignored)
├── .gitignore                          # Excludes .env, raw JSON, DuckDB binaries, logs
├── README.md                           # Main setup & execution documentation
├── TRACKER.md                          # This master project status file
├── LEARNINGS.md                        # Pharmacovigilance & technical architecture notes
├── ISSUES.md                           # Historical issues & bug resolutions log
├── requirements.txt                    # Python dependencies
├── start.sh                            # Shell script to run pipeline & launch dashboard
├── stop.sh                             # Shell script to stop Streamlit & background tasks
├── run_fast.py                         # Fast offline runner for analysis & charts
├── config/
│   └── drug_classes.yaml               # Configurable drug & MedDRA PT event definitions
├── data/
│   ├── raw/                            # 5.3 GB raw JSON responses from openFDA
│   ├── processed/                      # Cleaned CSVs (demographics, drugs, reactions, outcomes)
│   └── faers.duckdb                    # Local DuckDB database file
├── src/
│   ├── main.py                         # Complete pipeline orchestrator
│   ├── ingestion/openfda_client.py     # openFDA API client
│   ├── cleaning/data_cleaner.py       # Data parser, deduplicator, 2x2 table builder
│   ├── analysis/disproportionality.py  # ROR/PRR signal detection engine
│   └── visualization/charts.py         # 7 chart generators
├── dashboard/
│   └── app.py                          # Streamlit web dashboard
├── scripts/
│   └── upload_to_motherduck.py         # MotherDuck & local DuckDB sync script
├── reports/                            # Generated publication figures (.png)
└── tests/
    └── test_analysis.py                # 12 Pytest unit tests
```

---

## ⚙️ How to Run & Maintain

```bash
# Activate environment
source venv/bin/activate

# 1. Run full pipeline & launch dashboard
./start.sh

# 2. Stop dashboard & background tasks
./stop.sh

# 3. Fast offline re-analysis & chart regeneration
python run_fast.py

# 4. Sync data to MotherDuck cloud database
python scripts/upload_to_motherduck.py

# 5. Execute unit tests
python -m pytest tests/test_analysis.py -v
```

---

## 🎯 Future Scope / Next Phases

- [ ] Add support for additional drug classes (e.g. SGLT2 inhibitors, Statins, PPIs) in `config/drug_classes.yaml`
- [ ] Implement Bayesian Information Component (IC) and Empirical Bayes (EBGM) metrics
- [ ] Draft publication manuscript template using generated tables and figures
