from dbtunnel.tunnels import DbTunnel, DbTunnelProxy
from dbtunnel.utils import process_file, execute
from dbtunnel.vendor.asgiproxy.frameworks import Frameworks

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

        proxy_service = DbTunnelProxy(
            proxy_port=port,
            service_port=streamlit_service_port,
            url_base_path=url_base_path,
            framework=Frameworks.STREAMLIT,
            token_auth=self._basic_tunnel_auth["token_auth"],
            token_auth_workspace_url=self._basic_tunnel_auth["token_auth_workspace_url"],
            cwd=None
        )

        proxy_service.start()

        self._log.info(f"Use this link to access the Streamlit UI in Databricks: \n{self._proxy_settings.proxy_url}")

        with process_file(self._script_path) as file_path:
            self.run_streamlit(file_path, streamlit_service_port)

        proxy_service.wait()

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
