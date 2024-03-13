import io
import logging
import tarfile
import tempfile
import urllib.parse
from pathlib import Path

import aiohttp

LOG: logging.Logger = logging.getLogger(__name__)


class Gitlab:
    def __init__(self, hostname: str = "gitlab.esss.lu.se") -> None:
        self.hostname = hostname

    async def get_tar_ball(self, repo: str) -> Path:
        repo_name = repo.split("/")[1] + "-master"
        async with aiohttp.ClientSession() as asession:
            full_url = urllib.parse.urljoin(
                f"https://{self.hostname}",
                f"{repo}/-/archive/master/{repo_name}.tar.gz",
            )
            LOG.debug("GET tar from %s", full_url)
            async with asession.get(url=full_url) as result:
                content_bytes = await result.content.read()
                LOG.debug("Result tar size from %s", len(content_bytes))

                tar = tarfile.open(fileobj=io.BytesIO(content_bytes), mode="r|gz")
                temp_dir = tempfile.gettempdir()
                LOG.debug("Extracting files to %s", temp_dir)
                tar.extractall(path=temp_dir, filter=tarfile.data_filter)
                return Path(temp_dir).joinpath(repo_name).joinpath("files")
