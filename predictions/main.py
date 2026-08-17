"""
FPL predictions scraper — runs all registered agents and saves results.

Usage:
    python -m predictions                        # run all agents, auto-detect GW
    python -m predictions --agents solio         # run one agent
    python -m predictions --gw 5                 # force a specific GW
    python -m predictions --dry-run              # fetch + parse but don't save
    python -m predictions login                  # one-time browser login for planner agents
"""
import argparse
import logging
import sys
from datetime import datetime, timezone

import requests

from .agents.solio import SolioAgent
from .agents.solio_planner import SolioPlannerAgent
from .storage.writer import save_tables

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Register new agents here as you add them.
ALL_AGENTS = [
    SolioAgent,
    SolioPlannerAgent,
]


def _current_gw() -> int:
    """Ask the official FPL API for the current or next gameweek."""
    try:
        resp = requests.get(
            "https://fantasy.premierleague.com/api/bootstrap-static/",
            timeout=15,
        )
        resp.raise_for_status()
        events = resp.json()["events"]
        current = next((e for e in events if e["is_current"]), None)
        if current:
            return current["id"]
        nxt = next((e for e in events if e["is_next"]), None)
        if nxt:
            return nxt["id"]
    except Exception as exc:
        log.warning("GW auto-detect failed (%s); defaulting to 1", exc)
    return 1


def _do_login() -> int:
    """Open headed Chrome for a one-time manual Google login."""
    from playwright.sync_api import sync_playwright
    from .browser import create_browser_context, SOLIO_URL

    log.info("Opening browser — complete Google OAuth in the window that appears.")
    with sync_playwright() as p:
        ctx = create_browser_context(p, headless=False)
        page = ctx.new_page()
        page.goto(SOLIO_URL, wait_until="domcontentloaded")

        # Poll /api/auth/get-session until a real session appears (max 3 min)
        log.info("Waiting for you to log in... (up to 3 minutes)")
        for _ in range(180):
            try:
                resp = page.request.get(f"{SOLIO_URL}/api/auth/get-session", timeout=5_000)
                body = resp.text().strip()
                if resp.ok and body not in ("null", ""):
                    log.info("Session confirmed: %s", body[:120])
                    log.info("Login successful! Session saved to chrome_profile/")
                    ctx.close()
                    return 0
            except Exception:
                pass
            page.wait_for_timeout(1_000)

        log.error("Login timed out after 3 minutes.")
        ctx.close()
    return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="FPL prediction scraper")
    parser.add_argument(
        "--agents",
        nargs="*",
        metavar="NAME",
        help="Agent names to run (default: all). Example: --agents solio",
    )
    parser.add_argument(
        "--gw",
        type=int,
        metavar="N",
        help="Gameweek number (default: auto-detect from FPL API)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse but do not write to disk",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["login"],
        help="'login' opens a browser for one-time Google OAuth",
    )
    args = parser.parse_args(argv)

    if args.command == "login":
        return _do_login()

    gw = args.gw or _current_gw()
    agent_filter = set(args.agents) if args.agents else None
    fetched_at = datetime.now(timezone.utc)

    log.info("=== FPL predictions run  GW%02d  %s ===", gw, fetched_at.strftime("%Y-%m-%d %H:%M UTC"))

    errors: list[str] = []

    for AgentCls in ALL_AGENTS:
        agent = AgentCls()
        if agent_filter and agent.name not in agent_filter:
            continue

        log.info("[%s] fetching ...", agent.name)
        try:
            raw = agent.fetch_raw()

            # Cross-check: warn if the page reports a different GW than expected.
            if hasattr(agent, "parse_gw_from_page"):
                page_gw = agent.parse_gw_from_page(raw)
                if page_gw and page_gw != gw:
                    log.warning(
                        "[%s] page says GW%d but we're saving as GW%d — "
                        "pass --gw %d to override",
                        agent.name, page_gw, gw, page_gw,
                    )

            tables = agent.parse(raw)
            log.info("[%s] parsed %d tables: %s", agent.name, len(tables), ", ".join(tables))

            if not args.dry_run:
                save_tables(agent.name, gw, fetched_at, tables)
                log.info("[%s] done", agent.name)
            else:
                for slug, df in tables.items():
                    log.info("  [dry-run] %s: %d rows × %d cols", slug, *df.shape)

        except Exception as exc:
            log.error("[%s] FAILED: %s", agent.name, exc, exc_info=True)
            errors.append(agent.name)

    if errors:
        log.error("Agents with errors: %s", ", ".join(errors))
        return 1

    log.info("All agents completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
