from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
import pandas as pd

from .. import config

log = logging.getLogger(__name__)


def save_tables(
    vendor: str,
    gw: int,
    fetched_at: datetime,
    tables: dict[str, pd.DataFrame],
) -> dict[str, Path]:
    """Persist each table to disk under data/predictions/{vendor}/.

    Returns a dict mapping table slug → saved path.
    """
    date_str = fetched_at.strftime("%Y%m%d_%H%M")
    out_dir = config.DATA_DIR / vendor
    out_dir.mkdir(parents=True, exist_ok=True)

    saved: dict[str, Path] = {}
    for slug, df in tables.items():
        df = df.copy()
        df.insert(0, "vendor", vendor)
        df.insert(1, "gw", gw)
        df.insert(2, "fetched_at", fetched_at.isoformat())

        stem = f"{slug}_gw{gw:02d}_{date_str}"
        path = _write(df, out_dir / stem)
        saved[slug] = path
        log.info("    saved %s (%d rows)", path.name, len(df))

    return saved


def _write(df: pd.DataFrame, stem: Path) -> Path:
    """Write df to parquet; fall back to CSV if pyarrow is unavailable."""
    try:
        path = stem.with_suffix(".parquet")
        df.to_parquet(path, index=False)
        return path
    except Exception:
        path = stem.with_suffix(".csv")
        df.to_csv(path, index=False)
        return path
