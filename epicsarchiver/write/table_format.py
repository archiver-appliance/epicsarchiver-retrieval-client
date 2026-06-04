"""Terminal table formatter for archived events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from epicsarchiver.common.date_util import ResponseTimestamp

if TYPE_CHECKING:
    from datetime import datetime

    from epicsarchiver.retrieval.archive_event import ArchiveEvent, ArchiveEventsMeta
    from epicsarchiver.retrieval.client.processor import Processor


@dataclass
class FormatTable:
    """Renders a flat list of ArchiveEvents as a Rich table to the terminal."""

    events: list[ArchiveEvent]
    pvs: tuple[str, ...]
    start: datetime
    end: datetime
    processor: Processor | None
    meta: dict[int, ArchiveEventsMeta] | None

    def _meta_field_values(self) -> dict[int, dict[str, str]]:
        if not self.meta:
            return {}
        return {
            yr: {f.name: f.value or "" for f in m.headers if f.name}
            for yr, m in self.meta.items()
        }

    @staticmethod
    def _table_caption(field_values: dict[int, dict[str, str]]) -> str | None:
        if not field_values:
            return None
        lines = []
        for yr, fv_dict in field_values.items():
            lines.append(f"Field Values {yr}")
            lines.extend(f"{k}: {v}" for k, v in fv_dict.items())
        return "\n".join(lines)

    def _table_title(self) -> str:
        title = f"Period {self.start} - {self.end}"
        if len(self.pvs) == 1:
            title = f"{self.pvs[0]} {title}"
        if self.processor:
            title += f" Processor {self.processor.processor_name}"
            if self.processor.bin_size:
                title += f", {self.processor.bin_size} seconds"
        return title

    def _create_table(self, title: str, caption: str | None) -> Table:
        table = Table(title=title, caption=caption, caption_justify="left")
        table.add_column("PV", justify="left")
        table.add_column("Time", justify="left")
        table.add_column("Value", justify="right")
        table.add_column("Status", justify="right")
        table.add_column("Severity", justify="right")
        for event in self.events:
            table.add_row(
                event.pv,
                ResponseTimestamp(event.timestamp_ns).to_local_string(),
                str(event.val),
                str(event.status),
                str(event.severity),
            )
        return table

    def render(self) -> Table:
        """Render events as a Rich Table.

        Returns:
            Table: Rich Table ready to print.
        """
        return self._create_table(
            self._table_title(),
            self._table_caption(self._meta_field_values()),
        )

    def write(self) -> None:
        """Print the rendered table to the terminal."""
        Console().print(self.render())
