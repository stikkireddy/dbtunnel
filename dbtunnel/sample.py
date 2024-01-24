import asyncio
import functools
import re

from vendor.asgiproxy.config import BaseURLProxyConfigMixin, ProxyConfig
from vendor.asgiproxy.context import ProxyContext
from vendor.asgiproxy.simple_proxy import make_simple_proxy_app
import uvicorn

HOST = "localhost"
PORT = 5050

ROOT_PATH = "/example/world"


def _modify_root(content, root_path):
    list_of_uris = [b"/assets", b"/public"]
    for uri in list_of_uris:
        content = content.replace(uri, root_path.encode("utf-8") + uri)
    return content

def _modify_js_content_root_rewrite(content):
    # regex_pattern = r'\{path:"\/",element:y\.jsx\((\w+),\{\}\)\}'
    regex_pattern = r'\{path:"\/",element:(\w+)\.jsx\((\w+),\{\}\)\}'

    decoded_content = content.decode("utf-8")
    # Find all matches
    # find the default root function
    matches = re.findall(regex_pattern, decoded_content)

    # If there are matches, replace "*" part and print the modified code
    if matches:
        print(matches)
        jsx_call = matches[0][0]
        func = matches[0][1]  # Assuming there is only one match

        print(f"Found match: {jsx_call}, {func}")
        modified_code = re.sub(r'\{path:"\*",element:.*\.jsx\(.*,\{replace:!0,to:"\/"\}\)\}',
                               f'{{path:"*",element:{jsx_call}.jsx({func},{{}})}}', decoded_content)
        return modified_code.encode("utf-8")
    else:
        print("No match found.")
        return content

def _modify_js_bundle(content, root_path):
    list_of_uris = [b"/project/settings", b"/auth/config", b"/ws/socket.io"]
    for uri in list_of_uris:
        content = content.replace(uri, root_path.encode("utf-8") + uri)
    content = _modify_js_content_root_rewrite(content)
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
