import copy
import functools
import os
import threading

from dbtunnel.tunnels import DbTunnel
from dbtunnel.utils import make_asgi_proxy_app, execute


def make_gradio_local_proxy_config(
        url_base_path,
        service_host: str = "0.0.0.0",
        service_port: int = 9989,
        auth_config: dict = None):
    from dbtunnel.vendor.asgiproxy.config import BaseURLProxyConfigMixin, ProxyConfig
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


class GradioAppTunnel(DbTunnel):

    def __init__(self, gradio_app,
                 app_path: str,
                 cwd: str = None,
                 port: int = 8080):
        super().__init__(port, flavor="gradio")
        self._app_path = app_path
        self._cwd = cwd
        self._gradio_app = gradio_app

    def _imports(self):
        try:
            from fastapi import FastAPI
            import uvicorn
            import gradio as gr
            import nest_asyncio
        except ImportError as e:
            self._log.info("ImportError: Make sure you have fastapi, nest_asyncio uvicorn, gradio installed. \n"
                           "pip install fastapi nest_asyncio uvicorn gradio")
            raise e

    def _run(self):
        if self._gradio_app is not None:
            self._run_app()
            return

        self._log.info("Starting server...")
        import nest_asyncio
        nest_asyncio.apply()

        gradio_service_port = 9908
        port = self._port
        url_base_path = self._proxy_settings.url_base_path

        auth_config = copy.deepcopy(self._basic_tunnel_auth)

        def run_uvicorn_app():
            self._log.info("Starting proxy server...")
            app = make_asgi_proxy_app(make_gradio_local_proxy_config(
                url_base_path,
                service_port=gradio_service_port,
                auth_config=auth_config
            ))
            import uvicorn
            return uvicorn.run(host="0.0.0.0",
                               loop="asyncio",
                               port=int(port),
                               app=app,
                               root_path=url_base_path)

        uvicorn_thread = threading.Thread(target=run_uvicorn_app)
        # Start the thread in the background
        uvicorn_thread.start()
        self._log.info(f"Use this link to access the Streamlit UI in Databricks: \n{self._proxy_settings.proxy_url}")

        self._log.info("Starting gradio...")

        my_env = os.environ.copy()
        my_env["GRADIO_SERVER_PORT"] = str(gradio_service_port)
        my_env["GRADIO_SERVER_NAME"] = "0.0.0.0"

        cmd = ["python", self._app_path]

        self._log.info(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env, cwd=self._cwd):
            self._log.info(path)

    def _run_app(self):
        self.display()
        self._log.info("Starting server...")
        from fastapi import FastAPI
        import uvicorn
        import gradio as gr
        app = FastAPI(root_path=self._proxy_settings.url_base_path.rstrip("/"))
        app = gr.mount_gradio_app(app, self._gradio_app, path="/")
        import nest_asyncio
        nest_asyncio.apply()

        # Start the server
        async def start():
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=self._port,
            )
            server = uvicorn.Server(config)
            await server.serve()

        # Run the asyncio event loop instead of uvloop to enable re entrance
        import asyncio
        self._log.info(f"Use this link: \n{self._proxy_settings.proxy_url}")
        asyncio.run(start())

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'
