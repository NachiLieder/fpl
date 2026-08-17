"""Solio Analytics scraper.

Public endpoint: https://fpl.solioanalytics.com/api/data/latest
Returns server-rendered HTML with GW projections. No auth required.
Refreshes every 4 hours. Pro subscription gates the squad planner only.
"""
from __future__ import annotations

import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

from .base import BaseAgent

URL = "https://fpl.solioanalytics.com/api/data/latest"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; fpl-predictions-scraper/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}

# Maps a keyword in the section <h2> to a stable table slug.
_SECTION_SLUG = [
    ("top-projected", "projections"),
    ("captain",       "captains"),
    ("differential",  "differentials"),
    ("goals",         "goals"),
    ("assists",       "assists"),
    ("clean sheet",   "clean_sheets"),
    ("bonus",         "bonus"),
    ("defcon",        "defcon"),
    ("transfer",      "transfers"),
    ("attacking",     "fixtures"),
]


def _slug_from_heading(heading: str) -> str:
    h = heading.lower()
    for keyword, slug in _SECTION_SLUG:
        if keyword in h:
            return slug
    return re.sub(r"\W+", "_", h).strip("_")[:40]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = (
        df.columns.str.lower()
          .str.replace(r"[\.\s]+", "_", regex=True)
          .str.replace(r"[^a-z0-9_]", "", regex=True)
          .str.strip("_")
    )
    # '#' column (rank) normalizes to empty string — restore it
    cols = ["rank" if c == "" else c for c in cols]
    df.columns = cols
    return df


class SolioAgent(BaseAgent):
    name = "solio"

    def fetch_raw(self) -> str:
        resp = requests.get(URL, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.text

    def parse(self, raw: str) -> dict[str, pd.DataFrame]:
        soup = BeautifulSoup(raw, "lxml")
        tables: dict[str, pd.DataFrame] = {}

        for section in soup.find_all("section"):
            h2 = section.find("h2")
            table_el = section.find("table")
            if not h2 or not table_el:
                continue

            slug = _slug_from_heading(h2.get_text())
            df = pd.read_html(str(table_el))[0]
            df = _normalize_columns(df)
            tables[slug] = df

        return tables

    @staticmethod
    def parse_gw_from_page(raw: str) -> "int | None":
        """Extract the advertised GW number from the page h1."""
        soup = BeautifulSoup(raw, "lxml")
        h1 = soup.find("h1")
        if not h1:
            return None
        m = re.search(r"Gameweek\s+(\d+)", h1.get_text())
        return int(m.group(1)) if m else None
