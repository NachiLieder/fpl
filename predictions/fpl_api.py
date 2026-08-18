"""Thin wrapper around the official FPL bootstrap-static API.

Provides player metadata (ID, team, position) for enriching scraped data.
"""
from __future__ import annotations

import logging

import pandas as pd
import requests

log = logging.getLogger(__name__)

_FPL_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
_POS_MAP = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def fetch_players() -> pd.DataFrame:
    """Return a DataFrame with one row per FPL player.

    Columns: fpl_id, fpl_name, team, pos, price
    """
    resp = requests.get(_FPL_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    players = pd.DataFrame(data["elements"])[
        ["id", "web_name", "team", "element_type", "now_cost"]
    ]
    teams = (
        pd.DataFrame(data["teams"])[["id", "short_name"]]
        .rename(columns={"id": "team", "short_name": "team_short"})
    )
    players = players.merge(teams, on="team")
    players["pos"] = players["element_type"].map(_POS_MAP)
    players["price"] = players["now_cost"] / 10
    return (
        players.rename(columns={"id": "fpl_id", "web_name": "fpl_name"})
        [["fpl_id", "fpl_name", "team_short", "pos", "price"]]
    )


def enrich(df: pd.DataFrame, name_col: str = "name", price_col: str = "price") -> pd.DataFrame:
    """Add fpl_id, team, pos columns to *df* by joining on (name, price).

    Matching strategy:
      1. Exact (name, price) match — covers the vast majority.
      2. Name-only match — for the rare case where prices diverge by rounding.
    Ambiguous matches (same name + price at two clubs) log a warning and take the
    first FPL hit; fpl_id is still populated so downstream code can filter.
    Unmatched rows get NaN in the new columns.
    """
    fpl = fetch_players()
    log.info("FPL API: %d players loaded", len(fpl))

    # Round prices to 1 dp to handle any floating-point noise
    df = df.copy()
    df["_price_r"] = df[price_col].round(1)
    fpl["_price_r"] = fpl["price"].round(1)

    # Identify and warn about ambiguous (name, price) pairs before deduplication
    fpl_key = fpl.rename(columns={"fpl_name": name_col})
    ambiguous = fpl_key[fpl_key.duplicated(subset=[name_col, "_price_r"], keep=False)]
    if not ambiguous.empty:
        pairs = ambiguous.groupby([name_col, "_price_r"])["team_short"].apply(list)
        for (name, price), teams in pairs.items():
            log.warning(
                "Ambiguous FPL match: '%s' at £%.1f appears in %s — using %s",
                name, price, teams, teams[0],
            )
    # Deduplicate FPL lookup so merges stay 1-to-1 (keep first occurrence)
    fpl_deduped = fpl_key.drop_duplicates(subset=[name_col, "_price_r"])

    # Primary join: name + price
    merged = df.merge(
        fpl_deduped[[name_col, "_price_r", "fpl_id", "team_short", "pos"]],
        on=[name_col, "_price_r"],
        how="left",
    )

    # For rows still unmatched, try name-only join (picks first hit)
    unmatched = merged["fpl_id"].isna()
    if unmatched.any():
        log.warning(
            "%d rows unmatched after (name, price) join — falling back to name-only",
            unmatched.sum(),
        )
        name_lookup = fpl_deduped.drop_duplicates(subset=[name_col])[
            [name_col, "fpl_id", "team_short", "pos"]
        ]
        fallback = df[unmatched][[name_col]].merge(name_lookup, on=name_col, how="left")
        for col in ("fpl_id", "team_short", "pos"):
            merged.loc[unmatched, col] = fallback[col].values

    still_unmatched = merged["fpl_id"].isna().sum()
    if still_unmatched:
        log.warning(
            "%d rows still unmatched (new signings not yet in FPL API?): %s",
            still_unmatched,
            merged.loc[merged["fpl_id"].isna(), name_col].tolist()[:10],
        )

    return merged.drop(columns=["_price_r"]).rename(columns={"team_short": "team"})
