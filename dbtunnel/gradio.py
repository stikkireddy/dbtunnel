from dbtunnel.tunnels import DbTunnel


class GradioAppTunnel(DbTunnel):

    def __init__(self, gradio_app, port: int = 8080):
        super().__init__(port, flavor="gradio")
        self._gradio_app = gradio_app

    def _imports(self):
        try:
            from fastapi import FastAPI
            import uvicorn
            import gradio as gr
            import nest_asyncio
        except ImportError as e:
            print("ImportError: Make sure you have fastapi, nest_asyncio uvicorn, gradio installed. \n"
                  "pip install fastapi nest_asyncio uvicorn gradio")
            raise e

    def _run(self):
        self.display()
        print("Starting server...", flush=True)
        from fastapi import FastAPI
        import uvicorn
        import gradio as gr
        app = FastAPI(root_path=self._proxy_settings.url_base_path.rstrip("/"))
        app = gr.mount_gradio_app(app, self._gradio_app, path="/")
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
        print(f"Use this link: \n{self._proxy_settings.proxy_url}")
        asyncio.run(start())

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'
