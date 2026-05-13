"""Terminal table formatter for PV name search results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class SearchTable:
    """Formats a list of PV names into a Rich Table for the search command."""

    pvs: list[str]
    start: datetime | None
    end: datetime | None

    def _search_table_title(self) -> str:
        len_pvs = len(self.pvs)
        title = f"Found {len_pvs} PV{'s' if len_pvs > 1 else ''}"
        if self.start and self.end:
            title += f" between {self.start} and {self.end}"
        elif self.start:
            title += f" from {self.start} until now"
        elif self.end:
            title += f" before {self.end}"
        return title

    def _create_pv_name_table(self, title: str) -> Table:
        table = Table(title=title)
        table.add_column("PV name", justify="left")
        for pv in self.pvs:
            table.add_row(pv)
        return table

    def render(self) -> Table:
        """Return a Rich Table of PV names."""
        return self._create_pv_name_table(self._search_table_title())

    def write(self) -> None:
        """Print the search results table to the terminal."""
        Console().print(self.render())
