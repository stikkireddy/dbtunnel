import argparse
import asyncio
from typing import Tuple
from urllib.parse import urlparse

from starlette.types import ASGIApp

from dbtunnel.vendor.asgiproxy.config import BaseURLProxyConfigMixin, ProxyConfig
from dbtunnel.vendor.asgiproxy.context import ProxyContext
from dbtunnel.vendor.asgiproxy.frameworks import framework_specific_proxy_config
from dbtunnel.vendor.asgiproxy.simple_proxy import make_simple_proxy_app

try:
    import uvicorn
except ImportError:
    uvicorn = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--service-port", type=int, required=True)
    ap.add_argument("--token-auth", action='store_true', default=False)
    ap.add_argument("--token-auth-workspace-url", type=str, default=None)
    ap.add_argument("--host", type=str, default="0.0.0.0")
    ap.add_argument("--url-base-path", type=str, required=True)
    ap.add_argument("--framework", type=str, required=True)
    args = ap.parse_args()
    if not uvicorn:
        ap.error(
            "The `uvicorn` ASGI server package is required for the command line client."
        )
    print("Starting proxy server... with args: ", args)
    config = framework_specific_proxy_config[args.framework](**{
        "url_base_path": args.url_base_path,
        "service_host": args.host,
        "service_port": args.service_port,
        "auth_config": {"token_auth": args.token_auth, "token_auth_workspace_url": args.token_auth_workspace_url}
    })
    proxy_context = ProxyContext(config)
    app = make_simple_proxy_app(proxy_context, framework=args.framework, proxy_port=args.port)
    try:
        return uvicorn.run(host=args.host,
                           port=int(args.port),
                           app=app,
                           root_path=args.url_base_path)
    finally:
        asyncio.run(proxy_context.close())


if __name__ == "__main__":
    main()
