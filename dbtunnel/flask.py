from dbtunnel.tunnels import DbTunnel


class FlaskAppTunnel(DbTunnel):

    def __init__(self, flask_app, port: int = 8080):
        super().__init__(port, flavor="flask")
        self._flask_app = flask_app

    def _imports(self):
        try:
            import flask
            import nest_asyncio
        except ImportError as e:
            print("ImportError: Make sure you have flask and nest_asyncio installed;"
                  "pip install flask nest_asyncio")
            raise e

    def _run(self):
        self.display()
        print("Starting server...", flush=True)
        import nest_asyncio
        nest_asyncio.apply()
        async def start():
            await self._flask_app.run(host="0.0.0.0", port=self._port, url_prefix=self._proxy_settings.url_base_path)

        # Run the asyncio event loop instead of uvloop to enable re entrance
        import asyncio
        print(f"Use this link: \n{self._proxy_settings.proxy_url}")
        asyncio.run(start())

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'
