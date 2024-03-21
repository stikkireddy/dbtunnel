import os
import subprocess
import sys

from dbtunnel.tunnels import DbTunnel, DbTunnelProxy
from dbtunnel.utils import execute
from dbtunnel.vendor.asgiproxy.frameworks import Frameworks


def get_arize_projects_url(url: str):
    if url.endswith("/"):
        return f"{url}projects/"
    return f"{url}/projects/"


class ArizePhoenixUITunnel(DbTunnel):

    def __init__(self, port: int):
        super().__init__(port, "arize-phoenix")

    def _imports(self):
        try:
            import phoenix.server
            import nest_asyncio
        except ImportError as e:
            self._log.info("ImportError: Make sure you have chainlit installed. \n"
                           "pip install arize-phoenix nest_asyncio")
            raise e

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return (f'<a href="{get_arize_projects_url(self._proxy_settings.proxy_url)}">Click to go to {self._flavor} '
                f'App!</a>')

    def ui_url(self):
        self._display_html(f'<a href="{get_arize_projects_url(self._proxy_settings.proxy_url)}">'
                           f'Click to go to {self._flavor} App!</a> '
                           f'Use http://0.0.0.0:{self._port}/v1/traces for pushing arize traces.')

    def _run(self):
        self.display()
        self._log.info("Starting server...")

        phoenix_service_port_no_share = 9099
        proxy_service = None
        if self._share is False:
            url_base_path = self._proxy_settings.url_base_path
            port = self._port

            proxy_service = DbTunnelProxy(
                proxy_port=port,
                service_port=phoenix_service_port_no_share,
                url_base_path=url_base_path,
                framework=Frameworks.ARIZE_PHOENIX,
                token_auth=self._basic_tunnel_auth["token_auth"],
                token_auth_workspace_url=self._basic_tunnel_auth["token_auth_workspace_url"],
            )

            proxy_service.start()

        my_env = os.environ.copy()
        subprocess.run(f"kill -9 $(lsof -t -i:{self._port})", capture_output=True, shell=True)

        if self.shared is False:
            self._log.info(f"Deploying Arize Phoenix web ui app at path: "
                           f"\n{get_arize_projects_url(self._proxy_settings.proxy_url)}")

        if self._share is False:
            cmd = [sys.executable, "-m", "phoenix.server.main", "--port", f"{phoenix_service_port_no_share}",
                   "serve"]
        else:
            cmd = [sys.executable, "-m", "phoenix.server.main", "--port", f"{self._port}", "serve"]

        self._log.info(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env):
            self._log.info(path)

        if proxy_service is not None:
            proxy_service.wait()
