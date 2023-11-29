import abc
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal, Dict, Any

from dbtunnel.fastapi import FastApiAppTunnel
from dbtunnel.gradio import GradioAppTunnel
from dbtunnel.nicegui import NiceGuiAppTunnel
from dbtunnel.stable_diffusion_ui import StableDiffusionUITunnel
from dbtunnel.streamlit import StreamlitTunnel


@dataclass
class ProxySettings:
    proxy_url: str
    port: str
    url_base_path: str


Flavor = Literal["gradio", "fastapi", "nicegui", "streamlit", "stable-diffusion-ui"]


@contextmanager
def process_file(input_path):
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a temporary directory

        # Build the destination path in the temporary directory
        temp_file_path = os.path.join(temp_dir, os.path.basename(input_path))

        # Copy the file to the temporary directory
        shutil.copy(input_path, temp_file_path)

        # Yield the temporary file path to the caller
        yield temp_file_path
    finally:
        # Cleanup: Remove the temporary directory and its contents
        shutil.rmtree(temp_dir, ignore_errors=True)


def execute(cmd, env):
    import subprocess
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True, env=env)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


def get_cloud(context: Dict[str, Any]) -> str:
    # TODO: support gcp
    if context["extraContext"]["api_url"].endswith("azuredatabricks.net"):
        return "azure"
    return "aws"


def get_cloud_proxy_settings(cloud: str, org_id: str, cluster_id: str, port: int) -> ProxySettings:
    cloud_norm = cloud.lower()
    if cloud_norm not in ["aws", "azure"]:
        raise Exception("only supported in aws or azure")
    prefix_url_settings = {
        "aws": "https://dbc-dp-",
        "azure": "https://adb-dp-",
    }
    suffix_url_settings = {
        "aws": "cloud.databricks.com",
        "azure": "azuredatabricks.net",
    }
    # org_id = self._context["tags"]["orgId"]
    org_shard = ""
    # org_shard doesnt need a suffix of "." for dnsname its handled in building the url
    # only azure right now does dns sharding
    # gcp will need this
    if cloud_norm == "azure":
        org_shard_id = int(org_id) % 20
        org_shard = f".{org_shard_id}"
    # cluster_id = self._context["tags"]["clusterId"]
    url_base_path = f"/driver-proxy/o/{org_id}/{cluster_id}/{port}/"
    return ProxySettings(
        proxy_url=f"{prefix_url_settings[cloud_norm]}{org_id}{org_shard}.{suffix_url_settings[cloud_norm]}{url_base_path}",
        port=str(port),
        url_base_path=url_base_path
    )


class DbTunnel(abc.ABC):

    def __init__(self, port: int, flavor: Flavor):
        self._port = port
        self._flavor = flavor
        import IPython
        self._dbutils = IPython.get_ipython().user_ns["dbutils"]
        self._display_html = IPython.get_ipython().user_ns["displayHTML"]
        self._context = json.loads(self._dbutils.notebook.entry_point.getDbutils().notebook().getContext().toJson())
        self._org_id = self._context["tags"]["orgId"]
        self._cluster_id = self._context["tags"]["clusterId"]
        # need to do this after the context is set
        self._cloud = get_cloud(self._context)
        self._proxy_settings = get_cloud_proxy_settings(self._cloud, self._org_id, self._cluster_id,
                                                        self._port)

    @abc.abstractmethod
    def _imports(self):
        pass

    @abc.abstractmethod
    def _run(self):
        pass

    @abc.abstractmethod
    def _display_url(self):
        pass

    def run(self):
        self._imports()
        self._run()

    def display(self):
        self._display_html(self._display_url())


class AppTunnels:

    @staticmethod
    def fastapi(app, port: int = 8080):
        return FastApiAppTunnel(app, port)

    @staticmethod
    def gradio(app, port: int = 8080):
        return GradioAppTunnel(app, port)

    @staticmethod
    def nicegui(app, storage_secret: str = "", port: int = 8080):
        return NiceGuiAppTunnel(app, storage_secret, port)

    @staticmethod
    def streamlit(path, port: int = 8080):
        return StreamlitTunnel(path, port)

    @staticmethod
    def stable_diffusion_ui(no_gpu: bool, port: int = 7860):
        # todo auto detect with torch
        return StableDiffusionUITunnel(no_gpu, port)


dbtunnel = AppTunnels()
