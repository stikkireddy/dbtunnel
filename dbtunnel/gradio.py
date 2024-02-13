import functools
import functools
import os
import threading

from dbtunnel.tunnels import DbTunnel
from dbtunnel.utils import execute
from dbtunnel.vendor.asgiproxy.frameworks import Frameworks

class GradioAppTunnel(DbTunnel):

    def __init__(self, gradio_app,
                 app_path: str,
                 cwd: str = None,
                 port: int = 8080):
        super().__init__(port, flavor="gradio")
        self._app_path = app_path
        self._cwd = cwd
        self._gradio_app = gradio_app

    def _imports(self):
        try:
            from fastapi import FastAPI
            import uvicorn
            import gradio as gr
            import nest_asyncio
        except ImportError as e:
            self._log.info("ImportError: Make sure you have fastapi, nest_asyncio uvicorn, gradio installed. \n"
                           "pip install fastapi nest_asyncio uvicorn gradio")
            raise e

    def _run(self):
        if self._gradio_app is not None:
            self._run_app()
            return

        self._log.info("Starting server...")

        gradio_service_port = 9908
        port = self._port
        url_base_path = self._proxy_settings.url_base_path

        my_env = os.environ.copy()

        def run_uvicorn_app(env_copy):
            proxy_cmd = ["python", "-m", "dbtunnel.vendor.asgiproxy",
                         "--port", str(port),
                         "--service-port", str(gradio_service_port),
                         "--url-base-path", url_base_path,
                         "--framework", Frameworks.GRADIO]
            if self._basic_tunnel_auth["simple_auth"] is True:
                proxy_cmd.append("--token-auth")
            if self._basic_tunnel_auth["simple_auth_workspace_url"] is not None:
                proxy_cmd.append("--token-auth-workspace-url")
                proxy_cmd.append(self._basic_tunnel_auth["simple_auth_workspace_url"])

            self._log.info(f"Running proxy server via command: {' '.join(proxy_cmd)}")
            try:
                for log_stmt in execute(proxy_cmd, env_copy, cwd=self._cwd):
                    print(log_stmt)
            except Exception as e:
                self._log.info("Error running proxy server")

        uvicorn_thread = threading.Thread(target=run_uvicorn_app, args=(my_env,))
        uvicorn_thread.start()

        self._log.info(f"Use this link to access the Gradio UI in Databricks: \n{self._proxy_settings.proxy_url}")

        self._log.info("Starting gradio...")

        my_env = os.environ.copy()
        my_env["GRADIO_SERVER_PORT"] = str(gradio_service_port)
        my_env["GRADIO_SERVER_NAME"] = "0.0.0.0"

        cmd = ["python", self._app_path]

        self._log.info(f"Running command: {' '.join(cmd)}")
        for log_stmt in execute(cmd, my_env, cwd=self._cwd):
            self._log.info(log_stmt.rstrip("/n"))

        uvicorn_thread.join()

    def _run_app(self):
        self.display()
        self._log.info("Starting server...")
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
        self._log.info(f"Use this link: \n{self._proxy_settings.proxy_url}")
        asyncio.run(start())

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'
