import hashlib
import os
import re
import secrets
import shutil
import tarfile
import tempfile
import uuid
from typing import Optional, Literal, List

import requests

from dbtunnel.utils import execute

PRIVATE_SUBDOMAIN_PREFIX = "private-"


class ProxyWithNameAlreadyExists(Exception):
    pass

class StandardProxyError(Exception):
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


class DBTunnelRelaySecretTunnelCfg:

    # only used for more complex settings
    def __init__(self, *,
                 app_name,
                 visitor: bool,
                 tunnel_host="proxy.dbtunnel.app",
                 tunnel_port: int = 7000,
                 tunnel_type: Literal['stcp'] = 'stcp',  # secure tcp
                 server_secret: str = None,
                 bind_port: int = 4040,
                 bind_host: str = "0.0.0.0",
                 folder_name: str = ".dbtunnel", ):
        self._app_name = app_name
        self._tunnel_host = tunnel_host
        self._tunnel_port = tunnel_port
        self._tunnel_type = tunnel_type
        self._visitor = visitor
        if visitor is True and server_secret is None:
            raise ValueError(f"server_secret is required for visiting app: {app_name}")
        if visitor is False and server_secret is None:
            self._server_secret = secrets.token_urlsafe(32)
        else:
            self._server_secret = server_secret
        self._bind_port = bind_port
        self._bind_host = bind_host
        self._folder_name = folder_name
        self._setup()

    def get_cfg_path(self):
        folder_path = os.path.join(os.getcwd(), self._folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        # Create a file with syntax <visitor|secretserver>.app_name.toml
        file_name = f"{'visitor' if self._visitor is True else 'secretserver'}.{self._app_name}.toml"
        file_path = os.path.join(folder_path, file_name)
        return file_path

    def write_visitor_cfg(self, file_path: str):
        with open(file_path, "w") as f:
            f.write(f"serverAddr = \"{self._tunnel_host}\"\n")
            f.write(f"serverPort = {self._tunnel_port}\n")
            f.write(f"\n")
            f.write(f"[[visitors]]\n")
            f.write(f"name = \"{self._app_name}-visitor\"\n")
            f.write(f"type = \"{self._tunnel_type}\"\n")
            f.write(f"serverName = \"{self._app_name}\"\n")
            f.write(f"secretKey = \"{self._server_secret}\"\n")
            f.write(f"bindAddr = \"{self._bind_host}\"\n")
            f.write(f"bindPort = {self._bind_port}\n")

    def write_secret_server_cfg(self, file_path: str):
        with open(file_path, "w") as f:
            f.write(f"serverAddr = \"{self._tunnel_host}\"\n")
            f.write(f"serverPort = {self._tunnel_port}\n")
            f.write(f"\n")
            f.write(f"[[proxies]]\n")
            f.write(f"name = \"{self._app_name}\"\n")
            f.write(f"type = \"{self._tunnel_type}\"\n")
            f.write(f"secretKey = \"{self._server_secret}\"\n")
            f.write(f"localIP = \"{self._bind_host}\"\n")
            f.write(f"localPort = {self._bind_port}\n")

    def _setup(self):
        # Create .dbtunnel folder if it doesn't exist
        file_path = self.get_cfg_path()
        if self._visitor:
            self.write_visitor_cfg(file_path)
        else:
            self.write_secret_server_cfg(file_path)

    def get_cmd(self, executable: str) -> List[str]:
        return [executable, "-c", self.get_cfg_path()]


# TODO: break this class into more composable components
class DBTunnelRelayClient:
    def __init__(self, *,
                 local_port,
                 app_name,
                 tunnel_host,
                 log_level="info",
                 user: Optional[str] = None,
                 tunnel_port: int = 7000,
                 app_host: Optional[str] = None,
                 subdomain: Optional[str] = None,
                 local_host="0.0.0.0",
                 file_name: str = "dbtunnel.toml",
                 folder_name: str = ".dbtunnel",
                 executable_path: str = "frpc",
                 sso: bool = False,
                 mode: Literal['native', 'ssh'] = 'native',
                 secret: bool = False,
                 visitor: bool = False,
                 secret_string: Optional[str] = None,
                 ):
        # visitor requires secret to be true
        self._secret_string = secret_string
        self._visitor = visitor
        self._secret = secret
        self._log_level = log_level
        self._app_host = app_host
        self._sso = sso
        self._mode = mode
        self._app_name = app_name
        self._tunnel_host = tunnel_host
        self._tunnel_port = tunnel_port
        self._local_port = local_port
        self._local_host = local_host
        self._subdomain: str = self._handle_subdomain(subdomain or self._app_name or str(uuid.uuid4()), sso)
        self._file_name = file_name
        self._folder_name = folder_name
        self._executable_path = executable_path if isinstance(executable_path, str) else str(executable_path)
        self._user = user or os.getlogin().lower()
        self._setup()

    @staticmethod
    def _handle_subdomain(subdomain, is_sso):
        # ensure that the subdomain is url friendly
        if is_url_friendly(subdomain) is False:
            raise TunnelConfigError(f"App name {subdomain} should be alphanumeric ")

        if is_sso is True and subdomain.startswith(PRIVATE_SUBDOMAIN_PREFIX) is False:
            return f"{PRIVATE_SUBDOMAIN_PREFIX}{subdomain}"

        if is_sso is True and subdomain.startswith(PRIVATE_SUBDOMAIN_PREFIX) is True:
            raise TunnelConfigError(f"App name {subdomain} is already private please remove the private- prefix")

        if is_sso is False and subdomain.startswith(PRIVATE_SUBDOMAIN_PREFIX) is True:
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
            if any([item is None or isinstance(item, str) is False for item in cmd]):
                raise TunnelConfigError(f"Invalid command: {cmd}")
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
        if "start visitor success" in log_stmt:
            return True
        if "RemoteAddress" in log_stmt:
            return True
        return False

    @staticmethod
    def is_visitor_connection_error(stmt):
        return "start new visitor connection error" in stmt

    def _run(self, cmd: List[str], output_func=None, success_callback=None) -> None:
        r = re.compile(r".*start error: proxy.*already exists.*")
        env_copy = os.environ.copy()
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
            if self.is_visitor_connection_error(stmt):
                output_func(stmt.rstrip("\n"))
                raise StandardProxyError(f"Visitor connection error. Please check with provider if your server is still up.")
            output_func(stmt.rstrip("\n"))

    def get_secret_cmd(self) -> List[str]:
        self.validate()
        if self._mode == 'ssh':
            raise ValueError("Secret tunnel is not supported in ssh mode")
        cfg = DBTunnelRelaySecretTunnelCfg(
            app_name=self._app_name,
            visitor=self._visitor,
            server_secret=self._secret_string,
            tunnel_host=self._tunnel_host,
            tunnel_port=self._tunnel_port,
            tunnel_type="stcp",
            bind_port=self._local_port,
            bind_host=self._local_host,
            folder_name=self._folder_name
        )
        return cfg.get_cmd(self._executable_path)

    def run(self, output_func=None, success_callback=None) -> None:
        self.validate()
        output_func = output_func or print
        # Run the frpc command
        if self._secret is False:
            cmd = self._get_cmd()
            self._run(cmd, output_func, success_callback)
        else:
            cmd = self.get_secret_cmd()
            self._run(cmd, output_func, success_callback)

    def run_as_thread(self, output_func=None, success_callback=None):
        import threading
        t = threading.Thread(target=self.run, args=(output_func, success_callback,))
        t.start()
        return t

    def public_url(self):
        return f"https://{self._subdomain}.{self._app_host}"
