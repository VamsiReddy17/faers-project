# FAERS Pharmacovigilance Pipeline — Key Learnings & Domain Architecture

This document synthesizes key learnings across pharmacovigilance domain concepts, data pipeline engineering, statistical signal mining, and cloud database integration.

---

## 🔬 1. Pharmacovigilance & Disproportionality Methodology

### FDA Adverse Event Reporting System (FAERS)
- **Data Source**: Public FDA repository of post-marketing adverse event and medication error reports.
- **openFDA API**: Exposes FAERS data via REST API endpoints (`/drug/event.json`).
- **Primary Suspect Filter**: Only reports where `patient.drug.drugcharacterization == "1"` are selected as primary suspect reports, eliminating weak concomitant drug associations.

### Disproportionality Analysis Metrics

#### 2×2 Contingency Table Definition
For a target drug $D$ and target adverse event $E$ within a study cohort:

|  | Event $E$ Reported | Event $E$ Not Reported | Total |
| :--- | :---: | :---: | :---: |
| **Target Drug $D$** | $a$ | $b$ | $a + b$ |
| **Other Drugs in Cohort** | $c$ | $d$ | $c + d$ |
| **Total** | $a + c$ | $b + d$ | $N$ |

#### Reporting Odds Ratio (ROR)
Measures the odds of an event being reported for a specific drug compared to other drugs:
$$\text{ROR} = \frac{a \times d}{b \times c}$$

**95% Confidence Interval**:
$$\text{ln}(\text{ROR}) \pm 1.96 \times \sqrt{\frac{1}{a} + \frac{1}{b} + \frac{1}{c} + \frac{1}{d}}$$
$$\text{CI}_{95\%} = \left[\exp\left(\text{ln}(\text{ROR}) - 1.96 \cdot \text{SE}\right),\; \exp\left(\text{ln}(\text{ROR}) + 1.96 \cdot \text{SE}\right)\right]$$

#### Proportional Reporting Ratio (PRR)
Measures the proportion of reports for a specific event among all reports for the drug:
$$\text{PRR} = \frac{a / (a + b)}{c / (c + d)}$$

#### Signal Threshold Rules
A safety signal is flagged when:
- **ROR Criterion**: Lower bound of $95\%\text{ CI} > 1.0$ and $a \ge 3$.
- **PRR Criterion**: $\text{PRR} \ge 2.0$, $\chi^2 \ge 4.0$, and $a \ge 3$.

---

## 🛠️ 2. Data Engineering & API Gotchas

### openFDA API Rate Limits & Pagination
1. **Batch Size Limit (`limit=500`)**: Without an openFDA API key, requests with `limit=1000` trigger HTTP 403 Forbidden. Using `limit=500` ensures smooth pagination.
2. **Hard Skip Ceiling (`skip=25000`)**: openFDA enforces a maximum skip limit of 25,000 per query. For high-volume drugs, date ranges must be chunked into yearly/quarterly queries.
3. **URL Encoding Query Formatting**: Search queries containing boolean OR logic must use `+OR+` separators (e.g., `(patient.drug.openfda.generic_name:"clozapine"+OR+patient.drug.openfda.generic_name:"clozaril")`) rather than unencoded spaces.

### Deduplication Strategy
FAERS receives updated case versions for identical patient cases over time. 
- Deduplication sorts by `safetyreportid` and numeric `case_version`, retaining only the **latest case version**.
- In our dataset of 114,000 raw reports, deduplication eliminated **12,292 duplicate reports** (~10.8% duplicate rate).

### 2×2 Contingency Table Cohort Formula
When calculating $d$ (other drugs without event $E$), using the study cohort total $N_{\text{cohort}} = \text{nunique}(\text{safetyreportid})$ prevents negative cell values:
$$d = N_{\text{cohort}} - a - b - c$$

---

## ☁️ 3. DuckDB & MotherDuck Integration

### Version Compatibility
- MotherDuck serverless cloud supports DuckDB extension versions up to **`v1.5.4`**.
- Installing `duckdb==1.5.4` in Python avoids extension initialization errors.

### Local & Cloud Hybrid Strategy
- **Local (`data/faers.duckdb`)**: Allows the Streamlit dashboard to run offline queries in milliseconds.
- **Cloud (`md:faers_database`)**: Allows collaborators to query all 6 tables from the MotherDuck Web UI (`https://app.motherduck.com`) without installing local dependencies.

---

## 🎨 4. Frontend & Pandas Compatibility

- **Pandas 2.1+ Styler deprecation**: `Styler.applymap()` was removed in Pandas 2.1; `Styler.map()` must be used for conditional cell formatting in Streamlit dataframes.
