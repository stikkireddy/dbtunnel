from typing import Optional, Union, Iterable, Dict, Callable
from urllib.parse import urljoin

import aiohttp
from multidict import MultiDict
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.types import Scope
from starlette.websockets import WebSocket

Headerlike = MultiDict


class ProxyConfig:
    def get_upstream_url(self, *, scope: Scope) -> str:
        """
        Get the upstream URL for a client request.
        """
        raise NotImplementedError("...")

    def get_client_protocols(self, *, scope: Scope, headers: Headers) -> Iterable[str]:
        """
        Get client subprotocol list so it can be passed upstream.
        """
        return scope.get("subprotocols", [])

    def get_upstream_url_with_query(self, *, scope: Scope) -> str:
        """
        Get the upstream URL for a client request, including any query parameters to include.
        """
        # The default implementation simply appends the original URL's query string to the
        # upstream URL generated by `get_upstream_url`.
        url = self.get_upstream_url(scope=scope)
        query_string = scope.get("query_string")
        if query_string:
            sep = "&" if "?" in url else "?"
            url += "{}{}".format(sep, query_string.decode("utf-8"))
        return url

    def process_client_headers(self, *, scope: Scope, headers: Headers) -> Headerlike:
        """
        Process client HTTP headers before they're passed upstream.
        """
        return headers

    def process_upstream_headers(
            self, *, scope: Scope, proxy_response: aiohttp.ClientResponse
    ) -> Headerlike:
        """
        Process upstream HTTP headers before they're passed to the client.
        """
        headers = MultiDict(proxy_response.headers)
        return headers  # type: ignore

    def get_upstream_http_options(
            self, *, scope: Scope, client_request: Request, data
    ) -> dict:
        """
        Get request options (as passed to aiohttp.ClientSession.request).
        """
        return dict(
            method=client_request.method,
            url=self.get_upstream_url_with_query(scope=scope),
            data=data,
            headers=self.process_client_headers(
                scope=scope,
                headers=client_request.headers,
            ),
            allow_redirects=False,
        )

    def get_upstream_websocket_options(
            self, *, scope: Scope, client_ws: WebSocket
    ) -> dict:
        """
        Get websocket connection options (as passed to aiohttp.ClientSession.ws_connect).
        """
        return dict(
            method=scope.get("method", "GET"),
            url=self.get_upstream_url(scope=scope),
            headers=self.process_client_headers(scope=scope, headers=client_ws.headers),
            protocols=self.get_client_protocols(scope=scope, headers=client_ws.headers),
        )


class BaseURLProxyConfigMixin:
    upstream_base_url: str
    rewrite_host_header: Optional[str] = None
    modify_content: Optional[Dict[str, Callable[[str], str]]] = None
    token_auth: Optional[bool] = False
    token_auth_workspace_url: Optional[str] = None

    def get_upstream_url(self, scope: Scope) -> str:
        return urljoin(self.upstream_base_url, scope["path"])

    def process_client_headers(
            self, *, scope: Scope, headers: Headerlike
    ) -> Headerlike:
        """
        Process client HTTP headers before they're passed upstream.
        """
        if self.rewrite_host_header:
            headers = headers.mutablecopy()  # type: ignore
            headers["host"] = self.rewrite_host_header
        return super().process_client_headers(scope=scope, headers=headers)  # type: ignore
