from dbtunnel.tunnels import DbTunnel
from dbtunnel.utils import process_file, execute


class StreamlitTunnel(DbTunnel):

    def __init__(self, script_path: str, port: int):
        super().__init__(port, "streamlit")
        self._script_path = script_path

    def _imports(self):
        try:
            import streamlit
            import nest_asyncio
        except ImportError as e:
            print("ImportError: Make sure you have nest_asyncio, streamlit installed. \n"
                  "pip install nest_asyncio streamlit")
            raise e

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'

    def _run(self):
        self.display()
        print("Starting server...", flush=True)
        import nest_asyncio
        nest_asyncio.apply()
        print(f"Use this link: \n{self._proxy_settings.proxy_url}")
        with process_file(self._script_path) as file_path:
            self.run_streamlit(file_path, self._port)

    @staticmethod
    def run_streamlit(path, port):
        import os
        import subprocess
        my_env = os.environ.copy()
        my_env["STREAMLIT_SERVER_PORT"] = f"{port}"
        my_env["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
        my_env["STREAMLIT_SERVER_HEADLESS"] = "true"
        subprocess.run(f"kill -9 $(lsof -t -i:{port})", capture_output=True, shell=True)

        print(f"Deploying streamlit app at path: {path} on port: {port}")
        cmd = [
            "streamlit",
            "run",
            path,
            "--browser.gatherUsageStats",
            "false",
            "--server.fileWatcherType",
            "none"
        ]
        print(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env):
            print(path, end="")


def streamlit_patch_websockets_v2():
    from pathlib import Path
    import subprocess
    import streamlit
    p = Path(streamlit.__file__)
    _dir = (p.parent)
    process = subprocess.run(f"find {_dir} -type f -exec sed -i -e 's/\"stream\"/\"ws\"/g' {{}} \;",
                             capture_output=True, shell=True)
    return process.stdout.decode()
