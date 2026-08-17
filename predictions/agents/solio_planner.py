"""Solio planner agent — uses a persistent Playwright browser profile to
scrape the full player projections table from the authenticated planner UI.

The Projections tab uses Glide Data Grid (canvas-based, gdg- prefix).
The DOM accessibility overlay only shows ~20 visible rows at a time;
we scroll the canvas with mouse-wheel events to page through all 565 players.

Requires a one-time manual login:
    python -m predictions login
"""
from __future__ import annotations

import json
import logging
import os
import tempfile

import pandas as pd
from playwright.sync_api import sync_playwright, Page

from ..browser import SOLIO_URL, create_browser_context, is_logged_in
from ..fpl_api import enrich as fpl_enrich
from .base import BaseAgent

log = logging.getLogger(__name__)

# Column headers as seen in the Projections tab:  Name, Price, 1, 2, 3, 4, 5, Average
_COLLECT_ROWS_JS = """() => {
    const rows = [...document.querySelectorAll('[role="row"]')].slice(1); // skip header
    return rows.map(row => {
        const idx = row.getAttribute('aria-rowindex');
        const cells = [...row.querySelectorAll('[role="gridcell"], [role="cell"]')]
                      .map(c => c.innerText.trim());
        return { idx, cells };
    }).filter(r => r.cells.length > 0);
}"""

_GET_HEADERS_JS = """() => {
    return [...document.querySelectorAll('[role="columnheader"]')]
           .map(h => h.innerText.trim());
}"""


def _activate_projections_tab(page: Page) -> None:
    page.goto(SOLIO_URL, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(3_000)
    page.get_by_role("tab", name="Projections").click()
    page.wait_for_timeout(2_000)


def _scroll_and_collect(page: Page, total_rows: int) -> dict[str, list[str]]:
    """Page through the Glide Data Grid by setting dvn-scroller.scrollTop directly.

    dvn-scroller is GDG's actual scroll container (overflow:auto, scrollH≈17k).
    Setting scrollTop triggers React to re-render the accessibility overlay with
    the rows that are now in view.
    """
    collected: dict[str, list[str]] = {}

    def _collect_batch() -> int:
        prev = len(collected)
        for item in page.evaluate(_COLLECT_ROWS_JS):
            key = item["idx"] or (item["cells"][0] if item["cells"] else None)
            if key and item["cells"]:
                collected[key] = item["cells"]
        return len(collected) - prev

    scroll_info = page.evaluate("""() => {
        const el = document.querySelector('.dvn-scroller');
        return el ? { scrollH: el.scrollHeight, clientH: el.clientHeight } : null;
    }""")

    if not scroll_info:
        log.warning("dvn-scroller not found — returning initial rows only")
        _collect_batch()
        return collected

    scroll_h = scroll_info["scrollH"]
    client_h = scroll_info["clientH"]
    # Step size: ~80% of viewport height to ensure overlap between pages
    step = max(int(client_h * 0.8), 200)
    positions = list(range(0, scroll_h + step, step))
    log.info("Scrolling dvn-scroller: height=%d, step=%d, pages=%d", scroll_h, step, len(positions))

    for i, pos in enumerate(positions):
        page.evaluate(f"() => {{ const el = document.querySelector('.dvn-scroller'); if (el) el.scrollTop = {pos}; }}")
        page.wait_for_timeout(350)
        added = _collect_batch()
        log.debug("Page %d (scrollTop=%d): +%d rows, total=%d", i, pos, added, len(collected))

        if len(collected) >= total_rows - 2:
            log.info("All %d rows collected in %d pages", len(collected), i + 1)
            break

    log.info("Scroll extraction done: %d / %d rows", len(collected), total_rows)
    return collected


class SolioPlannerAgent(BaseAgent):
    """Authenticated planner scraper — returns full ~565-player projection list
    with GW1-5 projected points and average for each player."""

    name = "solio_planner"

    def fetch_raw(self) -> str:
        with sync_playwright() as p:
            ctx = create_browser_context(p, headless=True)
            page = ctx.new_page()
            try:
                if not is_logged_in(page):
                    snap = os.path.join(tempfile.gettempdir(), "solio_debug.png")
                    page.screenshot(path=snap)
                    log.error("Not logged in — screenshot at %s", snap)
                    raise RuntimeError("Not logged in. Run: python -m predictions login")

                _activate_projections_tab(page)

                grid = page.locator("table[role='grid']").first
                grid.wait_for(state="attached", timeout=15_000)

                total = int(grid.get_attribute("aria-rowcount") or "565")
                log.info("Grid has %d total rows", total)

                headers = page.evaluate(_GET_HEADERS_JS)
                log.info("Headers: %s", headers)

                collected = _scroll_and_collect(page, total)
            finally:
                ctx.close()

        rows = [cells for _, cells in sorted(collected.items(),
                                             key=lambda kv: int(kv[0]) if kv[0].isdigit() else 9999)]
        return json.dumps({"headers": headers, "rows": rows})

    def parse(self, raw: str) -> dict[str, pd.DataFrame]:
        data = json.loads(raw)
        headers = data["headers"]
        rows = data["rows"]

        if not rows:
            log.warning("No rows extracted")
            return {}

        # Rename numeric GW headers to gw_N for clarity
        clean_headers = []
        for h in headers:
            if h.isdigit():
                clean_headers.append(f"gw{h}_pts")
            else:
                clean_headers.append(h.lower().replace(" ", "_"))
        if not clean_headers:
            clean_headers = [f"col_{i}" for i in range(len(rows[0]))]

        n = len(clean_headers)
        padded = [r[:n] + [""] * max(0, n - len(r)) for r in rows]
        df = pd.DataFrame(padded, columns=clean_headers)

        # Cast numeric columns
        for col in df.columns:
            if col != "name":
                df[col] = pd.to_numeric(df[col], errors="ignore")

        # Enrich with FPL metadata (player ID, team, position)
        try:
            df = fpl_enrich(df)
            # Reorder: identity columns first
            leading = ["name", "fpl_id", "team", "pos", "price"]
            rest = [c for c in df.columns if c not in leading]
            df = df[leading + rest]
        except Exception as exc:
            log.warning("FPL API enrichment failed (continuing without it): %s", exc)

        return {"projections": df}
