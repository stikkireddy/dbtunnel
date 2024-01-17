from dbtunnel.tunnels import DbTunnel
from dbtunnel.utils import execute


class ChainlitAppTunnel(DbTunnel):

    def _imports(self):
        try:
            import chainlit
            import nest_asyncio
        except ImportError as e:
            print("ImportError: Make sure you have chainlit installed. \n"
                  "pip install chainlit nest_asyncio")
            raise e

    def _run(self):
        if self._share is False:
            raise Exception("Chainlit app must be shared to run. Please use .share_to_internet_via_ngrok(...)")

        print("Starting chainlit...", flush=True)

        import os
        import subprocess
        my_env = os.environ.copy()
        subprocess.run(f"kill -9 $(lsof -t -i:{self._port})", capture_output=True, shell=True)

        cmd = ["chainlit", "run", self._chainlit_script_path, "-h", "--host", "0.0.0.0", "--port", f"{self._port}"]
        print(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env, cwd=self._cwd):
            print(path, end="")

    def __init__(self, chainlit_script_path: str, cwd: str = None, port: int = 8000):
        super().__init__(port, "chainlit")
        self._chainlit_script_path = chainlit_script_path
        self._cwd = cwd

    def _display_url(self):
        return None
