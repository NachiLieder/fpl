from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd


class BaseAgent(ABC):
    """All vendor agents inherit from this. Each agent owns its fetch + parse logic."""

    name: str  # slug used in file paths and logging, e.g. "solio"

    @abstractmethod
    def fetch_raw(self) -> str:
        """Return raw response from the vendor (HTML, JSON as string, etc.)."""
        ...

    @abstractmethod
    def parse(self, raw: str) -> dict[str, pd.DataFrame]:
        """Parse raw response into named DataFrames.

        Keys are stable table slugs (e.g. "projections", "captains").
        Columns should be snake_case strings.
        """
        ...

    def run(self) -> dict[str, pd.DataFrame]:
        raw = self.fetch_raw()
        return self.parse(raw)
