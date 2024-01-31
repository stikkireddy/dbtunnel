from dbtunnel.tunnels import DbTunnel


class NiceGuiAppTunnel(DbTunnel):

    def __init__(self, ui, storage_secret: str = "", port: int = 8080):
        super().__init__(port, flavor="nicegui")
        self._nicegui_app = ui
        self._storage_secret = storage_secret

    def _imports(self):
        try:
            from fastapi import FastAPI
            import uvicorn
            import nicegui
            import nest_asyncio
        except ImportError as e:
            self._log.info("ImportError: Make sure you have fastapi, nest_asyncio uvicorn, nicegui installed. \n"
                  "pip install fastapi nest_asyncio uvicorn nicegui")
            raise e

    def _run(self):
        self.display()
        self._log.info("Starting server...")
        from fastapi import FastAPI
        import uvicorn
        app = FastAPI(root_path=self._proxy_settings.url_base_path.rstrip("/"))
        self._nicegui_app.run_with(
            app,
            storage_secret=self._storage_secret,
        )

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
