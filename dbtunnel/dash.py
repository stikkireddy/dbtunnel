from dbtunnel.tunnels import DbTunnel


class DashAppTunnel(DbTunnel):

    def __init__(self, dash_app, port: int = 8080):
        super().__init__(port, flavor="dash")
        self._dash_app = dash_app

    def _imports(self):
        try:
            from fastapi import FastAPI
            import uvicorn
            import dash
            import nest_asyncio
        except ImportError as e:
            self._log.info("ImportError: Make sure you have fastapi, nest_asyncio, dash and uvicorn installed;"
                  "pip install fastapi nest_asyncio dash uvicorn")
            raise e

    def _run(self):
        self.display()
        self._log.info("Starting server...")
        from fastapi import FastAPI
        import uvicorn
        from fastapi.middleware.wsgi import WSGIMiddleware
        app = FastAPI(root_path=self._proxy_settings.url_base_path.rstrip("/"))
        # DASH HACK
        del self._dash_app.config._read_only['requests_pathname_prefix']
        del self._dash_app.config._read_only['routes_pathname_prefix']
        self._dash_app.config.update({
            'routes_pathname_prefix': self._proxy_settings.url_base_path,
            'requests_pathname_prefix': self._proxy_settings.url_base_path
        })
        app.mount("/", WSGIMiddleware(self._dash_app.server))
        import nest_asyncio
        nest_asyncio.apply()

        # uvicorn.run(app, host="0.0.0.0", port=self._port)
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
