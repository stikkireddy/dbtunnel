import os
import subprocess

from dbtunnel.tunnels import DbTunnel, get_current_username
from dbtunnel.utils import execute


class CodeServerTunnel(DbTunnel):

    def __init__(self,
                 directory_path: str = None,
                 repo_name: str = None,
                 port: int = 9988,
                 extension_ids: list[str] = None):
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

        self._extension_ids = extension_ids or []

        # Continue with the initialization
        super().__init__(port, "code-server")

    def _imports(self):
        return None

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'

    def _install_databricks_cli(self):
        self._log.info("Attempting to install databricks cli")
        command = "curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh"
        env_copy = os.environ.copy()
        already_installed = False
        try:
            for stmt in execute([command], shell=True, env=env_copy):
                if "already exists" in stmt:
                    already_installed = True
                self._log.info(stmt)
        except subprocess.CalledProcessError as e:
            if already_installed is False:
                raise e
        self._log.info("Finished installing databricks cli")

    def _install_extension(self, env, extension_id: str):
        for stmt in execute(["code-server", "--install-extension", extension_id], shell=True, env=env):
            self._log.info(stmt)
        self._log.info(f"Finished Installed extension: {extension_id}")

    def _install_extensions(self, env, extensions: list[str]):
        for extension in extensions:
            self._install_extension(env, extension)

    def _run(self):
        import subprocess

        self._log.info(f"Use this link: \n{self._proxy_settings.proxy_url}?folder={self._dir_path}")
        self._log.info("It may take a 15-30 seconds for the code server to start up.")

        self._log.info("Installing code server")
        url = "https://code-server.dev/install.sh"
        # Equivalent Python subprocess command with piping
        subprocess.run(f'curl -fsSL {url} | sh', check=True, shell=True)
        self._log.info("Installed code server")

        self._install_databricks_cli()

        import os
        import subprocess
        my_env = os.environ.copy()
        my_env["VSCODE_PROXY_URI"] = self._proxy_settings.url_base_path + "wss"
        subprocess.run(f"kill -9 $(lsof -t -i:{self._port})", capture_output=True, shell=True)

        self._log.info(f"Installing default plugins!")
        default_plugins = [
            "ms-python.python",
            "ms-toolsai.jupyter",
            "ms-toolsai.jupyter-renderers",
            "ms-toolsai.jupyter-keymap",
            "ms-toolsai.vscode-jupyter-cell-tags",
            "databricks.databricks",
            "databricks.sqltools-databricks-driver",
            "rangav.vscode-thunder-client",
        ]
        self._install_extensions(my_env, list(set(default_plugins + self._extension_ids)))

        # "VSCODE_PROXY_URI=“./driver-proxy/o/<id>/1201-175053-rt06lneb/8080/wss” code-server --bind-addr 0.0.0.0:8080  --auth none"
        self._log.info(f"Deploying code server on port: {self._port}")
        cmd = ["code-server",
               "--bind-addr",
               f"0.0.0.0:{self._port}",
               "--auth",
               "none"]
        self._log.info(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env):
            self._log.info(path)