import asyncio
import functools

from vendor.asgiproxy.config import BaseURLProxyConfigMixin, ProxyConfig
from vendor.asgiproxy.context import ProxyContext
from vendor.asgiproxy.simple_proxy import make_simple_proxy_app
import uvicorn

HOST = "localhost"
PORT = 8000

ROOT_PATH = "/example/world"


def _modify_root(content, root_path):
    list_of_uris = [b"/assets", b"/public"]
    for uri in list_of_uris:
        content = content.replace(uri, root_path.encode("utf-8") + uri)
    return content

def _modify_js_bundle(content, root_path):
    list_of_uris = [b"/project/settings", b"/auth/config", b"/ws/socket.io"]
    for uri in list_of_uris:
        content = content.replace(uri, root_path.encode("utf-8") + uri)
    content = content.replace(b'{path:"*",element:E.jsx(MC,{replace:!0,to:"/"})}', b'{path:"*",element:E.jsx(PGt,{})}')
    return content

def _modify_settings(content, root_path):
    list_of_uris = [b"/public"]
    for uri in list_of_uris:
        content = content.replace(uri, root_path.encode("utf-8") + uri)
    return content


modify_root = functools.partial(_modify_root, root_path=ROOT_PATH)
modify_js_bundle = functools.partial(_modify_js_bundle, root_path=ROOT_PATH)
modify_settings = functools.partial(_modify_settings, root_path=ROOT_PATH)

config = type(
    "Config",
    (BaseURLProxyConfigMixin, ProxyConfig),
    {
        "upstream_base_url": f"http://{HOST}:{PORT}",
        "rewrite_host_header": f"{HOST}:{PORT}",
        "modify_content": {
            "/": modify_root,
            "": modify_root,
            "*assets/index-*.js": modify_js_bundle,
            "*settings": modify_settings
        }
    },
)()
proxy_context = ProxyContext(config)
app = make_simple_proxy_app(proxy_context)

if __name__ == "__main__":
    try:
        uvicorn.run(host="0.0.0.0", port=int(7878), app=app, root_path="/example/world")
    finally:
        asyncio.run(proxy_context.close())
