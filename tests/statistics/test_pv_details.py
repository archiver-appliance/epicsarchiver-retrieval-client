import json
import logging
from pathlib import Path

from rich.logging import RichHandler

from epicsarchiver.statistics.pv_details import DetailEnum, Details

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[RichHandler(rich_tracebacks=True)],
)
LOG: logging.Logger = logging.getLogger(__name__)


def test_convert_json_to_details_list() -> None:
    example_path = Path("tests/statistics/samples/example_pv_details.json")
    with example_path.open(encoding="locale") as json_data:
        data = json.load(json_data)
        result = Details.from_json(data)
        LOG.info(result)
        assert set(result.keys()) == set(DetailEnum)
        assert len(result) == len(DetailEnum)
