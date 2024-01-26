from dbtunnel.tunnels import DbTunnel


class FlaskAppTunnel(DbTunnel):

    def __init__(self, flask_app, port: int = 8080):
        super().__init__(port, flavor="flask")
        self._flask_app = flask_app

    def _imports(self):
        try:
            import flask
            import fastapi
            import uvicorn
            import nest_asyncio
        except ImportError as e:
            self._log.info("ImportError: Make sure you have flask, fastapi, uvicorn and nest_asyncio installed;"
                  "pip install flask fastapi uvicorn nest_asyncio")
            raise e

    def _run(self):
        self.display()
        self._log.info("Starting server...")
        import uvicorn
        from fastapi import FastAPI
        from fastapi.middleware.wsgi import WSGIMiddleware

        app = FastAPI(root_path=self._proxy_settings.url_base_path.rstrip("/"))
        app.mount("/", WSGIMiddleware(self._flask_app))
        import nest_asyncio
        nest_asyncio.apply()

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
