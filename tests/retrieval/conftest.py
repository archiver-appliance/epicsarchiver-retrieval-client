import httpx

def make_response_mock(body: bytes) -> httpx.Response:
    return httpx.Response(200, content=body)
