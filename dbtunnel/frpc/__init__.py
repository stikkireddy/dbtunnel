import os
import shutil
import tarfile
import tempfile
import uuid
from typing import Optional
import requests
import re

import toml

from dbtunnel.utils import execute


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


class ProxyWithNameAlreadyExists(Exception):
    pass


class DBTunnelConfig:
    def __init__(self, *, tunnel_host,
                 local_port,
                 app_name,
                 subdomain: Optional[str] = None,
                 tunnel_port: int = 7000,
                 local_host="0.0.0.0",
                 file_name: str = "dbtunnel.toml",
                 folder_name: str = ".dbtunnel",
                 executable_path: str = "frpc"):
        self._app_name = app_name
        self._tunnel_host = tunnel_host
        self._tunnel_port = tunnel_port
        self._local_port = local_port
        self._local_host = local_host
        self._subdomain: str = subdomain or self._app_name or str(uuid.uuid4())
        self._file_name = file_name
        self._folder_name = folder_name
        self._executable_path = executable_path
        self._setup()

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

    def publish(self):
        if self._subdomain.isalnum() is False:
            raise ValueError(f"Subdomain: {self._subdomain} and/or app_name: {self._app_name} should be alphanumeric")
        # Write the configuration to dbtunnel.toml file
        config_data = {
            'serverAddr': self._tunnel_host,
            'serverPort': self._tunnel_port,
            'webserver.port': 7500,
            'proxies': [{
                "name": self._app_name,
                "type": "http",
                "localIp": "0.0.0.0",
                "localPort": self._local_port,
                "subdomain": self._subdomain
            }]
        }

        file_path = os.path.join(os.getcwd(), self._folder_name, self._file_name)
        with open(file_path, 'w') as toml_file:
            toml.dump(config_data, toml_file)

    def _sanitize_log(self, log_stmt):
        # replace [.*\.go.*] with dbtunnel
        return re.sub(r"\[[^\[]*\.go:\d+\]", "[dbtunnel-client]", log_stmt)

    def run(self):
        # Run the frpc command
        r = re.compile(r".*start error: proxy.*already exists.*")
        env_copy = os.environ.copy()
        for stmt in execute([self._executable_path,
                             "-c", self.get_file_path()
                             ], env=env_copy):
            stmt = self._sanitize_log(stmt)
            if r.match(stmt):
                print(stmt.rstrip("\n"))
                raise ProxyWithNameAlreadyExists(f"Proxy [{self._app_name}] already exists."
                                                 f" Please use a different app name.")
            print(stmt.rstrip("\n"))

    def run_as_thread(self):
        import threading
        t = threading.Thread(target=self.run)
        t.start()
        return t

    def public_url(self):
        return f"https://{self._subdomain}.{self._tunnel_host}"
