from dbtunnel.tunnels import DbTunnel, DbTunnelProxy
from dbtunnel.vendor.asgiproxy.frameworks import Frameworks


class SchorleAppTunnel(DbTunnel):

    def __init__(self, schorle_app, port: int = 8080):
        super().__init__(port, flavor="schorle")
        self._schorle_app = schorle_app

    def _imports(self):
        try:
            import uvicorn
            import nest_asyncio
            import schorle
        except ImportError as e:
            self._log.info("ImportError: Make sure you have nest_asyncio and uvicorn installed;"
                           "pip install fastapi nest_asyncio uvicorn")
            raise e

    def _run(self):
        self.display()
        self._log.info("Starting server...")
        import nest_asyncio
        import uvicorn
        nest_asyncio.apply()

        gradio_service_port = 9908
        port = self._port
        url_base_path = self._proxy_settings.url_base_path

        proxy_service = DbTunnelProxy(
            proxy_port=port,
            service_port=gradio_service_port,
            url_base_path=url_base_path,
            framework=Frameworks.SCHORLE,
            token_auth=self._basic_tunnel_auth["token_auth"],
            token_auth_workspace_url=self._basic_tunnel_auth["token_auth_workspace_url"],
        )

        proxy_service.start()

        # Start the server
        async def start():
            config = uvicorn.Config(
                self._schorle_app,
                host="0.0.0.0",
                port=gradio_service_port,
            )
            server = uvicorn.Server(config)
            await server.serve()

        # Run the asyncio event loop instead of uvloop to enable re entrance
        import asyncio
        self._log.info(f"Use this link to access your uvicorn based app: \n{self._proxy_settings.proxy_url}")
        asyncio.run(start())

        proxy_service.wait()

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'
