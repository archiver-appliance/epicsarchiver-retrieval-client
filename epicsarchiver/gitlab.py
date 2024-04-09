"""Mini module for interacting with Gitlab."""

import io
import logging
import tarfile
import tempfile
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING

from epicsarchiver.service import ServiceClient

if TYPE_CHECKING:
    import asyncio

    import aiohttp

LOG: logging.Logger = logging.getLogger(__name__)


class Gitlab(ServiceClient):
    """Gitlab class for downloading from gitlab."""

    def __init__(self, fqdn: str = "gitlab.esss.lu.se") -> None:
        """Init the Gitlab class.

        Args:
            fqdn (str, optional): fqdn of the gitlab instance.
                Defaults to "gitlab.esss.lu.se".
        """
        self.fqdn = fqdn
        self.base_url = f"https://{fqdn}"
        self._sessions: dict[asyncio.AbstractEventLoop, aiohttp.ClientSession] = {}

    async def get_tar_ball(self, repo: Path) -> Path:
        """Fetch the tar ball from the input repository and store in a temp directory.

        Expects the repository to have a "files" subdirectory.

        Args:
            repo (Path): Path of the repo,
                for example archiver-appliance/archiver-appliance-config-aa-linac-prod.

        Returns:
            Path: Returns the path of the "files" directory after download.
        """
        repo_name = repo.name + "-master"
        full_url = urllib.parse.urljoin(
            self.base_url,
            f"{repo}/-/archive/master/{repo_name}.tar.gz",
        )
        LOG.debug("GET tar from %s", full_url)
        async with await self._get(full_url) as result:
            content_bytes = await result.content.read()
            LOG.debug("Result tar size from %s", len(content_bytes))

            tar = tarfile.open(fileobj=io.BytesIO(content_bytes), mode="r|gz")
            temp_dir = tempfile.gettempdir()
            LOG.debug("Extracting files to %s", temp_dir)
            tar.extractall(path=temp_dir, filter="data")
            return Path(temp_dir) / repo_name / "files"
