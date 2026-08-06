# FAERS Pharmacovigilance Project — Issues & Bug Resolution Log

This document records all technical issues, root causes, and resolutions encountered during pipeline development.

---

## 🐛 Issue 1: openFDA API HTTP 403 Forbidden with `limit=1000`

- **Symptom**: Ingestion failed with `HTTP Error 403: 403 Client Error: Forbidden for url...` when requesting 1,000 records per page.
- **Root Cause**: Without an openFDA API key, openFDA rate-limiting blocks bulk requests requesting `limit=1000`.
- **Resolution**:
  1. Reduced `MAX_LIMIT` in `src/ingestion/openfda_client.py` from `1000` to `500`.
  2. Fixed URL search query string encoding by replacing spaces with explicit `+OR+` separators.
  3. Added exponential backoff retry logic for HTTP 403 and 429 status codes.

---

## 🐛 Issue 2: Negative $d$ Cell Value in 2×2 Contingency Table Calculation

- **Symptom**: ROR output returned `0.0` for all drug-event pairs with $d = -24684$.
- **Root Cause**: `total_reports_in_db` passed to `build_contingency_table` was defaulting to 0 or total drug reports, causing $d = N - a - b - c$ to evaluate as $0 - (a+b+c)$, resulting in negative numbers.
- **Resolution**: Updated `src/main.py` and `run_fast.py` to calculate total unique patient reports in the study cohort:
  ```python
  total_cohort_reports = demographics_df["safetyreportid"].nunique()
  ```
  This fixed the contingency table math, resulting in **19 valid safety signals** being detected.

---

## 🐛 Issue 3: `AttributeError: 'NoneType' object has no attribute 'get'` in JSON Parser

- **Symptom**: Ingestion crashed during cleaning with `AttributeError: 'NoneType' object has no attribute 'get'`.
- **Root Cause**: openFDA JSON contains explicit `null` values for optional fields like `primarysource` or `patient`. `report.get("primarysource", {})` evaluates to `None` when `primarysource: null` exists in JSON, causing `None.get("qualification")` to crash.
- **Resolution**: Implemented fallback dictionary evaluation in `src/cleaning/data_cleaner.py`:
  ```python
  primary_source = report.get("primarysource") or {}
  reporter_type = primary_source.get("qualification", "Unknown")

  patient = report.get("patient") or {}
  for drug_entry in (patient.get("drug") or []):
      ...
  ```

---

## 🐛 Issue 4: Pandas 2.1 Deprecation `AttributeError: 'Styler' object has no attribute 'applymap'`

- **Symptom**: Streamlit dashboard crashed on Tab 2 with `AttributeError: 'Styler' object has no attribute 'applymap'`.
- **Root Cause**: Pandas 2.1+ removed `Styler.applymap()` in favor of `Styler.map()`.
- **Resolution**: Replaced `style.applymap(...)` with `style.map(...)` in `dashboard/app.py`:
  ```python
  st.dataframe(
      filtered_results[available_cols].style.map(
          lambda v: "background-color: #FDECEA" if v is True else "",
          subset=[c for c in ["Signal_ROR", "Signal_PRR", "Signal"] if c in available_cols],
      ),
      use_container_width=True,
      height=500,
  )
  ```

---

## 🐛 Issue 5: MotherDuck Extension Version Mismatch (DuckDB `v1.5.5` vs `v1.5.4`)

- **Symptom**: MotherDuck upload script failed with:
  `Your DuckDB version (v1.5.5) is not yet supported by MotherDuck. The latest supported version is v1.5.4.`
- **Root Cause**: `pip install duckdb` installed the latest DuckDB `1.5.5`, which exceeded MotherDuck's supported extension ceiling (`1.5.4`).
- **Resolution**: Explicitly pinned `duckdb==1.5.4` in `requirements.txt` and re-installed:
  ```bash
  pip install "duckdb==1.5.4"
  ```

---

## 🐛 Issue 6: DuckDB File Lock Conflict (`IO Error: Could not set lock...`)

- **Symptom**: Upload script failed with `_duckdb.IOException: IO Error: Could not set lock on file data/faers.duckdb: Conflicting lock is held...`.
- **Root Cause**: An open DuckDB CLI session or active Python process held a write lock on `data/faers.duckdb`.
- **Resolution**: Terminated background DuckDB processes before executing write operations:
  ```bash
  pkill -f duckdb
  ```
