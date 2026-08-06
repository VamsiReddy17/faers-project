# FAERS Pharmacovigilance Signal Mining Pipeline

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://faers-project.streamlit.app)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> 🌐 **Live Interactive Dashboard**: Explore the live pharmacovigilance web application at [**https://faers-project.streamlit.app**](https://faers-project.streamlit.app)

A configurable, end-to-end pipeline for mining safety signals from the FDA Adverse Event Reporting System (FAERS) using disproportionality analysis (ROR/PRR).

## Quick Start

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Set your openFDA API key for higher rate limits
export OPENFDA_API_KEY="your-key-here"

# 4. Run the full pipeline
python -m src.main

# 5. Launch the dashboard
streamlit run dashboard/app.py
```

## Project Structure

```
Faers Project/
├── config/
│   └── drug_classes.yaml        # Drug class + adverse event definitions
├── data/
│   ├── raw/                     # Raw API JSON responses
│   └── processed/               # Cleaned CSVs
├── src/
│   ├── __init__.py
│   ├── main.py                  # Pipeline orchestrator
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── openfda_client.py    # openFDA API client
│   ├── cleaning/
│   │   ├── __init__.py
│   │   └── data_cleaner.py      # Parsing, dedup, standardization
│   ├── analysis/
│   │   ├── __init__.py
│   │   └── disproportionality.py # ROR/PRR computation
│   └── visualization/
│       ├── __init__.py
│       └── charts.py            # All chart generators
├── dashboard/
│   └── app.py                   # Streamlit interactive dashboard
├── notebooks/
│   └── analysis.ipynb           # Exploratory analysis notebook
├── reports/                     # Generated figures & tables
├── tests/
│   └── test_analysis.py         # Unit tests
├── requirements.txt
└── README.md
```

## Methodology

### Disproportionality Measures

**Reporting Odds Ratio (ROR)**:
- Signal if lower bound of 95% CI > 1

**Proportional Reporting Ratio (PRR)**:
- Signal if PRR ≥ 2, Chi² ≥ 4, and N ≥ 3

### Data Source
- openFDA Drug Adverse Events API (`/drug/event.json`)
- Configurable time periods and drug classes

## Configuration

Edit `config/drug_classes.yaml` to define your analysis:

```yaml
drug_class: "Atypical Antipsychotics"
drugs:
  - generic_name: "risperidone"
    brand_names: ["risperdal"]
adverse_events:
  - name: "Weight Gain"
    meddra_pts: ["Weight increased", "Obesity"]
```

## License
This project uses publicly available FDA data via the openFDA API.
