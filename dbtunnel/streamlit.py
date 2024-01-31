import copy
import threading

from dbtunnel.tunnels import DbTunnel
from dbtunnel.utils import process_file, execute, make_asgi_proxy_app


def make_streamlit_local_proxy_config(service_host: str = "0.0.0.0",
                                      service_port: int = 9989,
                                      auth_config: dict = None):
    from dbtunnel.vendor.asgiproxy.config import BaseURLProxyConfigMixin, ProxyConfig
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


class StreamlitTunnel(DbTunnel):

    def __init__(self, script_path: str, port: int):
        super().__init__(port, "streamlit")
        self._script_path = script_path

    def _imports(self):
        try:
            import streamlit
            import nest_asyncio
        except ImportError as e:
            self._log.info("ImportError: Make sure you have nest_asyncio, streamlit installed. \n"
                           "pip install nest_asyncio streamlit")
            raise e

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'

    def _run(self):
        self.display()
        self._log.info("Starting server...")
        import nest_asyncio
        nest_asyncio.apply()

        streamlit_service_port = 9908
        port = self._port
        url_base_path = self._proxy_settings.url_base_path

        auth_config = copy.deepcopy(self._basic_tunnel_auth)

        def run_uvicorn_app():
            self._log.info("Starting proxy server...")
            app = make_asgi_proxy_app(make_streamlit_local_proxy_config(
                service_port=streamlit_service_port,
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

        with process_file(self._script_path) as file_path:
            self.run_streamlit(file_path, streamlit_service_port)

    def run_streamlit(self, path, port):
        import os
        import subprocess
        my_env = os.environ.copy()
        my_env["STREAMLIT_SERVER_PORT"] = f"{port}"
        my_env["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
        my_env["STREAMLIT_SERVER_HEADLESS"] = "true"
        subprocess.run(f"kill -9 $(lsof -t -i:{port})", capture_output=True, shell=True)

        self._log.info(f"Deploying streamlit app at path: {path} on port: {port}")
        cmd = [
            "streamlit",
            "run",
            path,
            "--browser.gatherUsageStats",
            "false",
            "--server.fileWatcherType",
            "none"
        ]
        self._log.info(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env):
            self._log.info(path.rstrip("\n"))


def streamlit_patch_websockets_v2():
    from pathlib import Path
    import subprocess
    import streamlit
    p = Path(streamlit.__file__)
    _dir = (p.parent)
    process = subprocess.run(f"find {_dir} -type f -exec sed -i -e 's/\"stream\"/\"ws\"/g' {{}} \;",
                             capture_output=True, shell=True)
    return process.stdout.decode()
