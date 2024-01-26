from dbtunnel.tunnels import DbTunnel
from dbtunnel.utils import execute, process_file


class BokehTunnel(DbTunnel):

    def __init__(self, script_path: str, port: int):
        super().__init__(port, "bokeh")
        self._script_path = script_path

    def _imports(self):
        try:
            import nest_asyncio
            import bokeh
        except ImportError as e:
            self._log.info("ImportError: Make sure you have nest_asyncio, bokeh installed. \n"
                  "pip install nest_asyncio bokeh")
            raise e

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'

    def _run(self):
        self.display()
        self._log.info("Starting server...")
        import nest_asyncio
        nest_asyncio.apply()
        self._log.info(f"Use this link: \n{self._proxy_settings.proxy_url}")
        with process_file(self._script_path) as file_path:
            self.run_bokeh(file_path, self._port)

    def run_bokeh(self, path, port):
        import os
        import subprocess
        my_env = os.environ.copy()
        subprocess.run(f"kill -9 $(lsof -t -i:{port})", capture_output=True, shell=True)
        # static assets otherwise get served by root and the root path is not allowed!
        my_env["BOKEH_RESOURCES"] = "cdn"
        self._log.info(f"Deploying {self._flavor} app at path: {path} on port: {port}")
        server_path_prefix = self._proxy_settings.url_base_path.rstrip('/').lstrip('/')
        cmd = ["bokeh",
               "serve",
               "--show",
               path,
               "--port",
               str(port),
               # "--prefix",
               # server_path_prefix
               ]
        self._log.info(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env):
            self._log.info(path)
