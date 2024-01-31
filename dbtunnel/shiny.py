from dbtunnel.tunnels import DbTunnel

class ShinyPythonAppTunnel(DbTunnel):

    def __init__(self, shiny_app, port: int = 8080):
        super().__init__(port, flavor="shiny-python")
        self._shiny_app = shiny_app

    def _imports(self):
        try:
            import shiny
            import uvicorn
            import nest_asyncio
        except ImportError as e:
            self._log.info("ImportError: Make sure you have shiny, nest_asyncio and uvicorn installed;"
                  "pip install fastapi nest_asyncio uvicorn")
            raise e

    def _run(self):
        self.display()
        self._log.info("Starting server...")
        import uvicorn
        import nest_asyncio
        nest_asyncio.apply()

        async def start():
            config = uvicorn.Config(
                self._shiny_app,
                host="0.0.0.0",
                port=self._port,
            )
            server = uvicorn.Server(config)
            await server.serve()

        # Run the asyncio event loop instead of uvloop to enable re entrance
        import asyncio
        self._log.info(f"Use this link: \n{self._proxy_settings.get_proxy_url(ensure_ends_with_slash=True)}")
        asyncio.run(start())

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'
