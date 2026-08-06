"""
MotherDuck & DuckDB Exporter for FAERS Pharmacovigilance Dataset

Uploads all processed FAERS tables (demographics, drugs, reactions, outcomes,
signal_results, signals_detected) to MotherDuck cloud database ('faers_database')
and creates a local 'data/faers.duckdb' database.
"""

import os
import sys
from pathlib import Path
import duckdb
from dotenv import load_dotenv

# 1. Load environment variables from .env file
env_path = Path(".env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"✓ Loaded environment variables from {env_path.absolute()}")
else:
    load_dotenv()

token = os.environ.get("MOTHERDUCK_TOKEN") or os.environ.get("motherduck_token")
if not token:
    print("⚠ MOTHERDUCK_TOKEN environment variable not found in .env or environment.")
    print("  Please ensure your .env file contains: MOTHERDUCK_TOKEN=your_token_here")
    # Prompting fallback instructions
    # If token is not set as env var, DuckDB might use saved motherduck token in ~/.duckdb

db_name = "faers_database"
processed_dir = Path("data/processed")

tables = {
    "demographics": processed_dir / "demographics.csv",
    "drugs": processed_dir / "drugs.csv",
    "reactions": processed_dir / "reactions.csv",
    "outcomes": processed_dir / "outcomes.csv",
    "signal_results": processed_dir / "signal_results.csv",
    "signals_detected": processed_dir / "signals_detected.csv",
}

# Verify CSV files exist
missing = [name for name, path in tables.items() if not path.exists()]
if missing:
    print(f"✗ Missing processed CSV files: {missing}")
    print("  Please run the pipeline first to generate data/processed/ CSVs.")
    sys.exit(1)

# -------------------------------------------------------------
# STEP 1: Create Local DuckDB Database ('data/faers.duckdb')
# -------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 1: CREATING LOCAL DUCKDB DATABASE (data/faers.duckdb)")
print("=" * 60)

local_db_path = Path("data/faers.duckdb")
local_con = duckdb.connect(str(local_db_path))

for table_name, csv_path in tables.items():
    print(f"  Creating local table '{table_name}' from {csv_path}...")
    local_con.execute(
        f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto('{csv_path}')"
    )
    count = local_con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    print(f"  ✓ Local table '{table_name}': {count:,} rows")

local_con.close()
print(f"\n✓ Local DuckDB created: {local_db_path.absolute()}")

# -------------------------------------------------------------
# STEP 2: Upload to MotherDuck Cloud Database ('faers_database')
# -------------------------------------------------------------
print("\n" + "=" * 60)
print(f"STEP 2: UPLOADING TO MOTHERDUCK ('{db_name}')")
print("=" * 60)

md_connection_str = f"md:{db_name}"
if token:
    md_connection_str = f"md:{db_name}?token={token}"

try:
    md_con = duckdb.connect(md_connection_str)
    print(f"✓ Connected to MotherDuck database '{db_name}'!")

    for table_name, csv_path in tables.items():
        print(f"  Uploading '{table_name}' to MotherDuck...")
        md_con.execute(
            f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto('{csv_path}')"
        )
        count = md_con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  ✓ MotherDuck table '{table_name}': {count:,} rows")

    md_con.close()

    print("\n" + "═" * 60)
    print("🎉 SUCCESS! All tables uploaded to MotherDuck 'faers_database'.")
    print("═" * 60)
    print("You can now query your database directly from the MotherDuck Web UI!")

except Exception as e:
    print(f"\n✗ Error connecting or uploading to MotherDuck: {e}")
    print("\nLocal DuckDB database 'data/faers.duckdb' was created successfully and can be used offline.")
