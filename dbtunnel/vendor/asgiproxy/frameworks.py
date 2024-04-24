import functools
import re

from dbtunnel.vendor.asgiproxy.config import BaseURLProxyConfigMixin, ProxyConfig


def _make_chainlit_local_proxy_config(
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

        # fix for chainlit threads lookup and redirects
        content = content.replace(b'`/thread/${d.id}`', f'`{root_path}thread/${{d.id}}`'.encode("utf-8"), 1)
        content = content.replace(b'"/thread/:id?"', f'"{root_path}thread/:id?"'.encode("utf-8"), 1)
        content = content.replace(b'"/element/:id"', f'"{root_path}element/:id"'.encode("utf-8"), 1)

        list_of_uris = [
            b"/feedback",
            b"/project",
            b"/auth/config",
            b"/ws/socket.io",
            b"/logo",
            b"/readme",
            b"/login",
            b"/auth"]
        for uri in list_of_uris:
            content = content.replace(uri, root_path.encode("utf-8") + uri)

        content = content.replace(b'to:"/",', f'to:"{root_path}",'.encode("utf-8"))
        content = _modify_js_content_root_rewrite(content)
        #
        content = content.replace(b'callbackUrl:"/"', f'callbackUrl: "{root_path}"'.encode("utf-8"))
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
                "/login": modify_root,
                "": modify_root,
                "*assets/index-*.js": modify_js_bundle,
                "*settings": modify_settings,
                "*assets/index-*.css": modify_css_bundle,
            },
            **auth_config
        },
    )()
    return config


def _make_streamlit_local_proxy_config(
        url_base_path: str,  # noqa
        service_host: str = "0.0.0.0",
        service_port: int = 9989,
        auth_config: dict = None
):
    auth_config = auth_config or {}

    config = type(
        "Config",
        (BaseURLProxyConfigMixin, ProxyConfig),
        {
            "upstream_base_url": f"http://{service_host}:{service_port}",
            "rewrite_host_header": f"{service_host}:{service_port}",
            **auth_config,
        },
    )()
    return config


def _make_gradio_local_proxy_config(
        url_base_path,
        service_host: str = "0.0.0.0",
        service_port: int = 9989,
        auth_config: dict = None
):
    auth_config = auth_config or {}

    def _modify_js_bundle(content, root_path):
        list_of_uris = [b"/theme.css", b"/info", b"/queue", b"/assets"]
        for uri in list_of_uris:
            content = content.replace(uri, root_path.rstrip("/").encode("utf-8") + uri)

        content = content.replace(b'to:"/",', f'to:"{root_path}",'.encode("utf-8"))
        return content

    modify_js_bundle = functools.partial(_modify_js_bundle, root_path=url_base_path)

    config = type(
        "Config",
        (BaseURLProxyConfigMixin, ProxyConfig),
        {
            "upstream_base_url": f"http://{service_host}:{service_port}",
            "rewrite_host_header": f"{service_host}:{service_port}",
            "modify_content": {
                "*assets/index-*.js": modify_js_bundle,
                # some reason gradio also has caps index bundled calling out explicitly
                "*assets/Index-*.js": modify_js_bundle,
            },
            **auth_config,
        },
    )()
    return config


def _make_arize_phoenix_local_proxy_config(
        url_base_path,
        service_host: str = "0.0.0.0",
        service_port: int = 9989,
        auth_config: dict = None
):
    auth_config = auth_config or {}

    def _modify_root(content, root_path):
        list_of_uris = [b"/index.css", b"/modernizr.js", b"/favicon.ico", b"/index.js", b"/graphql", b"/projects"]
        for uri in list_of_uris:
            content = content.replace(uri, root_path.encode("utf-8") + uri)
        return content

    def _modify_js_bundle(content, root_path):
        list_of_uris = [b"/graphql", b"/projects"]
        for uri in list_of_uris:
            content = content.replace(uri, root_path.rstrip("/").encode("utf-8") + uri)

        return content

    modify_root = functools.partial(_modify_root, root_path=url_base_path)
    modify_js_bundle = functools.partial(_modify_js_bundle, root_path=url_base_path)

    config = type(
        "Config",
        (BaseURLProxyConfigMixin, ProxyConfig),
        {
            "upstream_base_url": f"http://{service_host}:{service_port}",
            "rewrite_host_header": f"{service_host}:{service_port}",
            "modify_content": {
                "/": modify_root,
                "/projects/": modify_root,
                "/projects/*": modify_root,
                "*/index.js": modify_js_bundle,
                # some reason gradio also has caps index bundled calling out explicitly
            },
            **auth_config,
        },
    )()
    return config


class Frameworks:
    STREAMLIT: str = "streamlit"
    GRADIO: str = "gradio"
    CHAINLIT: str = "chainlit"
    ARIZE_PHOENIX: str = "arize_phoenix"


framework_specific_proxy_config = {
    Frameworks.STREAMLIT: _make_streamlit_local_proxy_config,
    Frameworks.GRADIO: _make_gradio_local_proxy_config,
    Frameworks.CHAINLIT: _make_chainlit_local_proxy_config,
    Frameworks.ARIZE_PHOENIX: _make_arize_phoenix_local_proxy_config,
}
