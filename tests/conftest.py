"""Fail every test before any real Meta HTTP transport can reach a socket."""
import httpx,pytest
from urllib.parse import urlsplit

@pytest.fixture(autouse=True)
def no_real_meta_transport(monkeypatch):
    domains={'graph.facebook.com','graph.instagram.com','api.instagram.com','www.instagram.com','www.facebook.com'}
    original=httpx.HTTPTransport.handle_request
    async_original=httpx.AsyncHTTPTransport.handle_async_request
    def guarded(self,request):
        if request.url.host in domains:raise AssertionError('Real Meta transport forbidden')
        return original(self,request)
    async def async_guarded(self,request):
        if request.url.host in domains:raise AssertionError('Real Meta transport forbidden')
        return await async_original(self,request)
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',guarded)
    monkeypatch.setattr(httpx.AsyncHTTPTransport,'handle_async_request',async_guarded)
