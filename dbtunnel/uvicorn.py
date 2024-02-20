from dbtunnel.tunnels import DbTunnel


class UvicornAppTunnel(DbTunnel):

    def __init__(self, asgi_app, port: int = 8080):
        super().__init__(port, flavor="uvicorn")
        self._asgi_app = asgi_app

    def _imports(self):
        try:
            import uvicorn
            import nest_asyncio
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

        # Start the server
        async def start():
            config = uvicorn.Config(
                self._asgi_app,
                host="0.0.0.0",
                port=self._port,
                root_path=self._proxy_settings.url_base_path.rstrip("/")
            )
            server = uvicorn.Server(config)
            await server.serve()

        # Run the asyncio event loop instead of uvloop to enable re entrance
        import asyncio
        self._log.info(f"Use this link to access your uvicorn based app: \n{self._proxy_settings.proxy_url}")
        asyncio.run(start())

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'
