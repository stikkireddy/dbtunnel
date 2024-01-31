import tempfile

from dbtunnel.tunnels import DbTunnel
from dbtunnel.utils import execute


class StableDiffusionUITunnel(DbTunnel):

    def __init__(self, no_gpu: bool, port: int, enable_insecure_extensions: bool, extra_flags: str):
        super().__init__(port, "stable-diffusion-ui")
        self._no_gpu = no_gpu
        self._enable_insecure_extensions = enable_insecure_extensions
        self._extra_flags = extra_flags

    def _imports(self):
        return None

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'

    def _run(self):
        self.display()
        self._log.info("Starting server...")
        import requests
        import os
        script_url = "https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui/master/webui.sh"

        # Download the script
        response = requests.get(script_url)
        script_content = response.text

        # Create a temporary file to save the script
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as script_file:
            script_file.write(script_content)
            script_path = script_file.name

        # Set environment variable
        os.environ["COMMANDLINE_ARGS"] = ""

        # skip adding base path if sharing out via tunneling tech
        if self.shared is False:
            os.environ["COMMANDLINE_ARGS"] += f"--subpath={self._proxy_settings.url_base_path.rstrip('/').lstrip('/')} "

        # Set environment variable
        if self._no_gpu:
            os.environ["COMMANDLINE_ARGS"] += (
                f"--skip-torch-cuda-test ")
        # else:
        #     os.environ["COMMANDLINE_ARGS"] = f"--subpath={self._proxy_settings.url_base_path.rstrip('/').lstrip('/')}"

        if self._enable_insecure_extensions:
            os.environ["COMMANDLINE_ARGS"] += " --enable-insecure-extension-access "

        if len(self._extra_flags) > 0:
            os.environ["COMMANDLINE_ARGS"] += f" {self._extra_flags}"

        import os
        import subprocess
        my_env = os.environ.copy()
        subprocess.run(f"kill -9 $(lsof -t -i:{self._port})", capture_output=True, shell=True)

        if self.shared is False:
            self._log.info(f"Deploying stable diffusion web ui app at path: \n{self._proxy_settings.proxy_url}")

        cmd = ["bash", script_path, "-f", "--listen"]
        self._log.info(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env):
            self._log.info(path)
