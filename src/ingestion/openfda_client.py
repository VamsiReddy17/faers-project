"""
openFDA API Client for FAERS Adverse Event Data

Handles querying the /drug/event.json endpoint with pagination,
rate limiting, and caching of raw responses.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

import requests
from tqdm import tqdm


class OpenFDAClient:
    """Client for the openFDA Drug Adverse Events API."""

    BASE_URL = "https://api.fda.gov/drug/event.json"
    MAX_SKIP = 25000  # openFDA hard limit on skip parameter
    MAX_LIMIT = 500   # Max results per request (1000 returns 403 without API key)

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit_delay: float = 0.3,
        raw_data_dir: str = "data/raw",
    ):
        """
        Initialize the openFDA client.

        Args:
            api_key: openFDA API key (or set OPENFDA_API_KEY env var).
                     Without a key, rate limit is ~40 req/min.
                     With a key, it's ~240 req/min.
            rate_limit_delay: Seconds to wait between API calls.
            raw_data_dir: Directory to cache raw JSON responses.
        """
        self.api_key = api_key or os.environ.get("OPENFDA_API_KEY")
        self.rate_limit_delay = rate_limit_delay
        self.raw_data_dir = Path(raw_data_dir)
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _build_search_query(
        self,
        drug_names: list[str],
        start_date: str,
        end_date: str,
        primary_suspect_only: bool = True,
    ) -> str:
        """
        Build the openFDA search query string.

        Args:
            drug_names: List of generic drug names to search.
            start_date: Start date in YYYYMMDD format.
            end_date: End date in YYYYMMDD format.
            primary_suspect_only: If True, only include reports where the
                                  drug is the primary suspect.

        Returns:
            The search query string for the API.
        """
        # Build drug name filter (OR across all names)
        drug_terms = "+OR+".join(
            [f'patient.drug.openfda.generic_name:"{name}"' for name in drug_names]
        )
        drug_filter = f"({drug_terms})"

        # Date range filter
        date_filter = f"receivedate:[{start_date}+TO+{end_date}]"

        # Primary suspect filter
        parts = [drug_filter, date_filter]
        if primary_suspect_only:
            parts.append('patient.drug.drugcharacterization:"1"')

        return "+AND+".join(parts)

    def _make_request(
        self, search: str, skip: int = 0, limit: int = 1000, _retries: int = 3
    ) -> Optional[dict]:
        """
        Make a single API request.

        Args:
            search: The search query string.
            skip: Number of results to skip (for pagination).
            limit: Number of results to return (max 1000).
            _retries: Internal retry counter.

        Returns:
            JSON response as dict, or None if request fails.
        """
        # Build URL manually to avoid double-encoding of the search query
        url = f"{self.BASE_URL}?search={search}&skip={skip}&limit={limit}"
        if self.api_key:
            url += f"&api_key={self.api_key}"

        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                print(f"  No results found for skip={skip}")
                return None
            elif response.status_code == 429:
                print("  Rate limited! Waiting 60 seconds...")
                time.sleep(60)
                return self._make_request(search, skip, limit, _retries)
            elif response.status_code == 403:
                if _retries > 0:
                    wait = (4 - _retries) * 5
                    print(f"  403 Forbidden — retrying in {wait}s (retries left: {_retries})...")
                    time.sleep(wait)
                    return self._make_request(search, skip, limit, _retries - 1)
                else:
                    print(f"  403 Forbidden — exhausted retries for skip={skip}")
                    return None
            else:
                print(f"  HTTP Error {response.status_code}: {e}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"  Request failed: {e}")
            return None

    def get_total_count(
        self,
        drug_names: list[str],
        start_date: str,
        end_date: str,
        primary_suspect_only: bool = True,
    ) -> int:
        """
        Get total number of matching reports without downloading data.

        Returns:
            Total count of matching reports.
        """
        search = self._build_search_query(
            drug_names, start_date, end_date, primary_suspect_only
        )
        result = self._make_request(search, skip=0, limit=1)
        if result and "meta" in result:
            total = result["meta"]["results"]["total"]
            print(f"  Total matching reports: {total:,}")
            return total
        return 0

    def fetch_drug_events(
        self,
        drug_name: str,
        drug_names_all: list[str],
        start_date: str,
        end_date: str,
        primary_suspect_only: bool = True,
        max_records: Optional[int] = None,
    ) -> list[dict]:
        """
        Fetch all adverse event reports for a specific drug.

        openFDA limits skip to 25,000, so for drugs with more reports,
        we split by year to stay within limits.

        Args:
            drug_name: The specific generic drug name to query.
            drug_names_all: All names to include (generic + brand).
            start_date: Start date YYYYMMDD.
            end_date: End date YYYYMMDD.
            primary_suspect_only: Only primary suspect reports.
            max_records: Optional cap on total records to fetch.

        Returns:
            List of adverse event report dicts.
        """
        print(f"\n{'='*60}")
        print(f"Fetching reports for: {drug_name.upper()}")
        print(f"Period: {start_date} to {end_date}")
        print(f"{'='*60}")

        # Check cache first
        cache_file = self.raw_data_dir / f"{drug_name}_{start_date}_{end_date}.json"
        if cache_file.exists():
            print(f"  Loading from cache: {cache_file}")
            with open(cache_file, "r") as f:
                return json.load(f)

        all_results = []
        search = self._build_search_query(
            drug_names_all, start_date, end_date, primary_suspect_only
        )

        # Get total count
        total = self.get_total_count(
            drug_names_all, start_date, end_date, primary_suspect_only
        )
        if total == 0:
            return []

        # Determine how many to fetch
        fetch_count = min(total, self.MAX_SKIP, max_records or total)
        num_pages = (fetch_count + self.MAX_LIMIT - 1) // self.MAX_LIMIT

        print(f"  Fetching {fetch_count:,} reports in {num_pages} pages...")

        for page in tqdm(range(num_pages), desc=f"  {drug_name}"):
            skip = page * self.MAX_LIMIT
            if max_records and len(all_results) >= max_records:
                break

            result = self._make_request(search, skip=skip, limit=self.MAX_LIMIT)
            if result and "results" in result:
                all_results.extend(result["results"])
            else:
                break

            time.sleep(self.rate_limit_delay)

        print(f"  Retrieved {len(all_results):,} reports for {drug_name}")

        # Cache results
        with open(cache_file, "w") as f:
            json.dump(all_results, f)
        print(f"  Cached to: {cache_file}")

        return all_results

    def fetch_background_counts(
        self,
        event_terms: list[str],
        start_date: str,
        end_date: str,
    ) -> dict[str, int]:
        """
        Get total report counts for specific adverse events across ALL drugs.
        Uses the openFDA count endpoint for efficiency.

        Args:
            event_terms: List of MedDRA preferred terms to count.
            start_date: Start date YYYYMMDD.
            end_date: End date YYYYMMDD.

        Returns:
            Dict mapping event term → total count across all drugs.
        """
        print("\nFetching background event counts...")
        counts = {}

        date_filter = f"receivedate:[{start_date}+TO+{end_date}]"

        for term in tqdm(event_terms, desc="  Background counts"):
            search = f'{date_filter}+AND+patient.reaction.reactionmeddrapt:"{term}"'
            result = self._make_request(search, skip=0, limit=1)
            if result and "meta" in result:
                counts[term.lower()] = result["meta"]["results"]["total"]
            else:
                counts[term.lower()] = 0
            time.sleep(self.rate_limit_delay)

        return counts

    def get_total_reports_count(self, start_date: str, end_date: str) -> int:
        """
        Get the total number of ALL adverse event reports in the database
        for the given time period. Used as denominator for PRR.

        Returns:
            Total report count.
        """
        print("\nFetching total database report count...")
        search = f"receivedate:[{start_date}+TO+{end_date}]"
        result = self._make_request(search, skip=0, limit=1)
        if result and "meta" in result:
            total = result["meta"]["results"]["total"]
            print(f"  Total reports in FAERS ({start_date}-{end_date}): {total:,}")
            return total
        return 0
