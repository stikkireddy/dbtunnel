import functools
import functools
import re

from dbtunnel.tunnels import DbTunnel, DbTunnelProxy
from dbtunnel.utils import execute
from dbtunnel.vendor.asgiproxy.frameworks import Frameworks

def make_chainlit_local_proxy_config(
                                     url_base_path: str,
                                     service_host: str = "0.0.0.0",
                                     service_port: int = 9989,
                                     auth_config: dict = None
):
    from dbtunnel.vendor.asgiproxy.config import BaseURLProxyConfigMixin, ProxyConfig
    proxy_root_path = url_base_path
    auth_config = auth_config or {}

    def _modify_root(content, root_path):
        list_of_uris = [b"/assets", b"/public", b"/favicon"]
        for uri in list_of_uris:
            content = content.replace(uri, root_path.encode("utf-8") + uri)
        return content

    def _modify_js_content_root_rewrite(content):
        regex_pattern = r'\{path:"\/",element:(\w+)\.jsx\((\w+),\{\}\)\}'

        decoded_content = content.decode("utf-8")
        # Find all matches
        # find the default root function
        matches = re.findall(regex_pattern, decoded_content)
        if matches:
            jsx_call = matches[0][0]
            func = matches[0][1]  # Assuming there is only one match
            modified_code = re.sub(r'\{path:"\*",element:.*\.jsx\(.*,\{replace:!0,to:"\/"\}\)\}',
                                   f'{{path:"*",element:{jsx_call}.jsx({func},{{}})}}', decoded_content)
            return modified_code.encode("utf-8")
        else:
            print("No match found.")
            return content

    def _modify_js_bundle(content, root_path):
        list_of_uris = [b"/project/settings", b"/auth/config", b"/ws/socket.io", b"/logo", b"/readme"]
        for uri in list_of_uris:
            content = content.replace(uri, root_path.encode("utf-8") + uri)
        
        content = content.replace(b'to:"/",',f'to:"{root_path}",'.encode("utf-8"))
        content = _modify_js_content_root_rewrite(content)
        return content
    
    def modify_css_bundle(content):
        add_to_end = b" #new-chat-button {display: none;}"
        return content + add_to_end

    def _modify_settings(content, root_path):
        list_of_uris = [b"/public"]
        for uri in list_of_uris:
            content = content.replace(uri, root_path.encode("utf-8") + uri)
        return content

    modify_root = functools.partial(_modify_root, root_path=proxy_root_path)
    modify_js_bundle = functools.partial(_modify_js_bundle, root_path=proxy_root_path)
    modify_settings = functools.partial(_modify_settings, root_path=proxy_root_path)

    config = type(
        "Config",
        (BaseURLProxyConfigMixin, ProxyConfig),
        {
            "upstream_base_url": f"http://{service_host}:{service_port}",
            "rewrite_host_header": f"{service_host}:{service_port}",
            "modify_content": {
                "/": modify_root,
                "": modify_root,
                "*assets/index-*.js": modify_js_bundle,
                "*settings": modify_settings,
                "*assets/index-*.css": modify_css_bundle,
            },
            **auth_config
        },
    )()
    return config


class ChainlitAppTunnel(DbTunnel):

    def _imports(self):
        try:
            import chainlit
            import nest_asyncio
        except ImportError as e:
            self._log.info("ImportError: Make sure you have chainlit installed. \n"
                  "pip install chainlit nest_asyncio")
            raise e

    def _run(self):
        import os

        chainlit_service_port_no_share = 9090
        proxy_service = None
        if self._share is False:

            url_base_path = self._proxy_settings.url_base_path
            port = self._port

            # nest uvicorn to the ipynotebook asyncio eventloop so restarting kernel kills server
            proxy_service = DbTunnelProxy(
                proxy_port=port,
                service_port=chainlit_service_port_no_share,
                url_base_path=url_base_path,
                framework=Frameworks.CHAINLIT,
                token_auth=self._basic_tunnel_auth["token_auth"],
                token_auth_workspace_url=self._basic_tunnel_auth["token_auth_workspace_url"],
                cwd=self._cwd
            )

            proxy_service.start()

        self._log.info(f"Use this link to access the Chainlit UI in Databricks: \n{self._proxy_settings.proxy_url}")

        self._log.info("Starting chainlit...")

        my_env = os.environ.copy()

        if self._share is False:
            cmd = ["chainlit", "run", self._chainlit_script_path, "-h", "--host", "0.0.0.0", "--port",
                   f"{chainlit_service_port_no_share}"]
        else:
            cmd = ["chainlit", "run", self._chainlit_script_path, "-h", "--host", "0.0.0.0", "--port", f"{self._port}"]

        self._log.info(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env, cwd=self._cwd):
            self._log.info(path)

        if proxy_service is not None:
            proxy_service.wait()

    def __init__(self, chainlit_script_path: str, cwd: str = None, port: int = 8000):
        super().__init__(port, "chainlit")
        self._chainlit_script_path = chainlit_script_path
        self._cwd = cwd

    def _display_url(self):
        return None
