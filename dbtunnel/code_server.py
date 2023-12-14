import json
import os
import subprocess
import sys

from dbtunnel.tunnels import DbTunnel, get_current_username, PROXY_SETTINGS_ENV_VAR_CONF
from dbtunnel.utils import execute


def create_default_python_interpreter(path: str):
    with open(path, "w") as f:
        f.write(json.dumps({
            "python.defaultInterpreterPath": str(sys.executable)
        }, indent=4))

class CodeServerTunnel(DbTunnel):

    def __init__(self, 
                 directory_path: str = None, 
                 repo_name: str = None, 
                 config_save_path: str = None,
                 port: int = 9988):
        # Check if either directory_path or repo_name is provided
        if directory_path is None and repo_name is None:
            raise ValueError("Either directory_path or repo_name must be provided.")

        if repo_name:
            repo_path = f"/Workspace/Repos/{get_current_username()}/{repo_name}"
            if not os.path.exists(repo_path):
                raise ValueError(f"The provided repo_name '{repo_name}' in path: {repo_path} does not exist.")
            self._dir_path = repo_path

        # Check if directory_path is provided and exists
        if directory_path:
            if not os.path.exists(directory_path):
                raise ValueError(f"The provided directory_path '{directory_path}' does not exist.")
            self._dir_path = directory_path

        if config_save_path is None:
            self._config_save_path = f'/root/code-server/config/{get_current_username()}/defaults'# set XDG_DATA_HOME
        else:
            self._config_save_path = config_save_path

        # Continue with the initialization
        super().__init__(port, "code-server")

    def _imports(self):
        return None

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'

    def _run(self):
        file_path = "/usr/lib/code-server/lib/vscode/bin/remote-cli/code-server"

        if os.path.exists(file_path):
            print(f"The file {file_path} exists.")
        else:
            print(f"The file {file_path} does not exist.")
            print("Installing code server")
            url = "https://code-server.dev/install.sh"
            # Equivalent Python subprocess command with piping
            subprocess.run(f'curl -fsSL {url} | sh', check=True, shell=True)
            print("Installed code server")

        my_env = os.environ.copy()
        my_env["VSCODE_PROXY_URI"] = self._proxy_settings.url_base_path + "wss"
        my_env["XDG_DATA_HOME"] = str(self._config_save_path)
        create_default_python_interpreter(os.path.join(self._config_save_path, "code-server", "User", "settings.json"))
        my_env[PROXY_SETTINGS_ENV_VAR_CONF] = self._proxy_conf.to_json()

        subprocess.run(f"kill -9 $(lsof -t -i:{self._port})", capture_output=True, shell=True)
        print("Installing extensions")
        extensions = ["ms-python.python", 
                      "ms-toolsai.jupyter",
                      "ms-toolsai.jupyter-renderers", 
                      "ms-toolsai.jupyter-keymap",
                      "ms-toolsai.vscode-jupyter-cell-tags",
                      "ms-toolsai.vscode-jupyter-slideshow",
                      "luma.jupyter", 
                      "databricks.databricks", 
                      "databricks.sqltools-databricks-driver"]
        for ext in extensions:
            print(f"Installing extensions: {ext}")
            subprocess.run(f"code-server --install-extension {ext}", capture_output=True, shell=True, env=my_env)
        print("Finished extensions")

        # "VSCODE_PROXY_URI=“./driver-proxy/o/<org>/<clusterid>/8080/wss” code-server --bind-addr 0.0.0.0:8080  --auth none"
        print(f"Deploying code server on port: {self._port}")
        print(f"Use this link: \n{self._proxy_settings.proxy_url}?folder={self._dir_path}")
        cmd = ["code-server",
               "--bind-addr",
               f"0.0.0.0:{self._port}",
               "--auth",
               "none"]
        print(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env):
            print(path, end="")