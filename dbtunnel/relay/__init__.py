import os
import re
import shutil
import tarfile
import tempfile
import uuid
from typing import Optional, Literal

import requests

from dbtunnel.utils import execute

PRIVATE_SUBDOMAIN_PREFIX = "private-"


class ProxyWithNameAlreadyExists(Exception):
    pass


class TunnelConfigError(Exception):
    pass


def is_url_friendly(subdomain: str):
    try:
        return all(c.isalnum() or c in "-_" for c in subdomain)
    except ValueError:
        return False


def download_and_copy(url, destination_dir):
    # Create a temporary directory
    frpc_dest_path = os.path.join(destination_dir, 'frpc')
    if os.path.exists(frpc_dest_path):
        print(f"'frpc' already exists in {destination_dir}. Skipping download.")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        # Download the file
        response = requests.get(url, stream=True)
        file_name = url.split("/")[-1]
        temp_file_path = os.path.join(temp_dir, file_name)

        with open(temp_file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        # Extract the tar.gz file
        with tarfile.open(temp_file_path, 'r:gz') as tar:
            tar.extractall(path=temp_dir)

        # Copy the frpc file to the destination directory
        frpc_file_path = os.path.join(temp_dir, 'frp_0.54.0_linux_amd64', 'frpc')
        shutil.copy(frpc_file_path, destination_dir)


class DBTunnelRelayClient:
    def __init__(self, *,
                 local_port,
                 app_name,
                 log_level="info",
                 user: Optional[str] = None,
                 tunnel_host="proxy.dbtunnel.app",
                 tunnel_port: int = 7000,
                 app_host: Optional[str] = "dbtunnel.app",
                 subdomain: Optional[str] = None,
                 local_host="0.0.0.0",
                 file_name: str = "dbtunnel.toml",
                 folder_name: str = ".dbtunnel",
                 executable_path: str = "frpc",
                 private: bool = False,
                 mode: Literal['native', 'ssh'] = 'native'):
        self._log_level = log_level
        self._app_host = app_host
        self._private = private
        self._mode = mode
        self._app_name = app_name
        self._tunnel_host = tunnel_host
        self._tunnel_port = tunnel_port
        self._local_port = local_port
        self._local_host = local_host
        self._subdomain: str = self._handle_subdomain(subdomain or self._app_name or str(uuid.uuid4()), private)
        self._file_name = file_name
        self._folder_name = folder_name
        self._executable_path = executable_path if isinstance(executable_path, str) else str(executable_path)
        self._user = user or os.getlogin().lower()
        self._setup()

    @staticmethod
    def _handle_subdomain(subdomain, is_private):
        # ensure that the subdomain is url friendly
        if is_url_friendly(subdomain) is False:
            raise TunnelConfigError(f"App name {subdomain} should be alphanumeric ")

        if is_private is True and subdomain.startswith(PRIVATE_SUBDOMAIN_PREFIX) is False:
            return f"{PRIVATE_SUBDOMAIN_PREFIX}{subdomain}"

        if is_private is True and subdomain.startswith(PRIVATE_SUBDOMAIN_PREFIX) is True:
            raise TunnelConfigError(f"App name {subdomain} is already private please remove the private- prefix")

        if is_private is False and subdomain.startswith(PRIVATE_SUBDOMAIN_PREFIX) is True:
            raise TunnelConfigError(f"App name {subdomain} is private please add make sure you"
                                    f" create the tunnel in private mode")

        return subdomain

    def get_file_path(self):
        return os.path.join(os.getcwd(), self._folder_name, self._file_name)

    def download_on_linux(self):
        url = "https://github.com/fatedier/frp/releases/download/v0.54.0/frp_0.54.0_linux_amd64.tar.gz"
        download_and_copy(url, os.path.join(os.getcwd(), self._folder_name))
        self._executable_path = os.path.join(os.getcwd(), self._folder_name, "frpc")

    def _setup(self):
        # Create .dbtunnel folder if it doesn't exist
        folder_path = os.path.join(os.getcwd(), self._folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    def validate(self):
        if is_url_friendly(self._subdomain) is False:
            raise ValueError(
                f"Subdomain: {self._subdomain} should be url friendly. Only alphanumeric, hyphen and "
                f"underscore are allowed.")

    def _sanitize_log(self, log_stmt):
        if self._mode == "native":
            # replace [.*\.go.*] with dbtunnel
            return re.sub(r"\[[^\[]*\.go:\d+\]", "[dbtunnel-client]", log_stmt)
        if self._mode == "ssh":
            if "frp (via SSH)" in log_stmt:
                return None
            if log_stmt.strip() == "":
                return None
            if log_stmt.startswith("RemoteAddress"):
                return f"RemoteAddress: {self.public_url()}"
            return log_stmt

    def _get_cmd(self):
        if self._mode == 'native':
            # return [self._executable_path, "-c", self.get_file_path()]
            cmd = [self._executable_path,
                    "http",
                    "--server-addr",
                    self._tunnel_host,
                    "--server-port",
                    str(self._tunnel_port),
                    "--sd",
                    self._subdomain,
                    "-n",
                    self._app_name,
                    "--local-port",
                    str(self._local_port),
                    "--local-ip",
                    self._local_host,
                    "--ue",
                    "--uc",
                    "--log-level",
                    self._log_level,
                    "--user",
                    self._user]
            return cmd

        else:
            return ["ssh", "-R",
                    f":8000:{self._local_host}:{self._local_port}",
                    f"v0@{self._tunnel_host}", "-p",
                    "7200", "http",
                    "--proxy_name", self._app_name,
                    "--sd", self._subdomain,
                    "-u", self._user]

    @staticmethod
    def has_relay_conn_started(log_stmt: str):
        if "start proxy success" in log_stmt:
            return True
        if "RemoteAddress" in log_stmt:
            return True
        return False

    def run(self, output_func=None, success_callback=None):
        output_func = output_func or print
        # Run the frpc command
        r = re.compile(r".*start error: proxy.*already exists.*")
        env_copy = os.environ.copy()
        cmd = self._get_cmd()
        for stmt in execute(cmd, env=env_copy):
            stmt = self._sanitize_log(stmt)
            if stmt is None:
                continue
            if self.has_relay_conn_started(stmt) and success_callback is not None:
                success_callback()
            if r.match(stmt):
                output_func(stmt.rstrip("\n"))
                raise ProxyWithNameAlreadyExists(f"Proxy [{self._app_name}] already exists."
                                                 f" Please use a different app name.")
            output_func(stmt.rstrip("\n"))

    def run_as_thread(self, output_func=None, success_callback=None):
        import threading
        t = threading.Thread(target=self.run, args=(output_func, success_callback,))
        t.start()
        return t

    def public_url(self):
        return f"https://{self._subdomain}.{self._app_host}"
