"""Persistent Playwright browser context shared by all browser-based agents.

The Chrome profile lives at predictions/chrome_profile/ and survives across
runs — this is how we avoid re-doing Google OAuth every time.

First-time setup:
    python -m predictions login
"""
from __future__ import annotations

from pathlib import Path
from playwright.sync_api import BrowserContext, Playwright

CHROME_PROFILE_DIR = Path(__file__).parent / "chrome_profile"
SOLIO_URL = "https://fpl.solioanalytics.com"


def create_browser_context(playwright: Playwright, headless: bool = True) -> BrowserContext:
    CHROME_PROFILE_DIR.mkdir(exist_ok=True)
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(CHROME_PROFILE_DIR),
        headless=headless,
        args=["--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )


def is_logged_in(page) -> bool:
    """Check session via /api/auth/get-session — the only reliable indicator."""
    import logging
    log = logging.getLogger(__name__)
    try:
        page.goto(SOLIO_URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(2_000)
        resp = page.request.get(f"{SOLIO_URL}/api/auth/get-session", timeout=10_000)
        body = resp.text()
        log.debug("get-session response: %s", body[:200])
        return resp.ok and body not in ("null", "", "null\n")
    except Exception as exc:
        log.warning("is_logged_in check failed: %s", exc)
        return False
