from dbtunnel.tunnels import DbTunnel, DbTunnelProxy
from dbtunnel.utils import execute
from dbtunnel.vendor.asgiproxy.frameworks import Frameworks

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
