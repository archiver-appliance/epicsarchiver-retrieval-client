from unittest.mock import AsyncMock, MagicMock


def make_response_mock(body: bytes) -> MagicMock:
    mock = MagicMock()
    mock.content.read = AsyncMock(return_value=body)
    return mock
