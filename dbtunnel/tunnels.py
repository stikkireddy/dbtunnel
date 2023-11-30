import abc
import asyncio
import json
import os
import secrets
import string
import subprocess
from dataclasses import dataclass
from typing import Dict, Any, Literal

from dbtunnel.utils import run_secrets_proxy


@dataclass
class ProxySettings:
    proxy_url: str
    port: str
    url_base_path: str


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


Flavor = Literal["gradio", "fastapi", "nicegui", "streamlit", "stable-diffusion-ui", "bokeh", "flask"]


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
        self._loop = None

    @abc.abstractmethod
    def _imports(self):
        pass

    @abc.abstractmethod
    def _run(self):
        pass

    @abc.abstractmethod
    def _display_url(self):
        pass

    def with_secrets_proxy(self, port: int = 9898,
                           env_mode_var="DBTUNNEL_MODE",
                           secret_env_key="DBTUNNEL_CLIENT_SECRET",
                           client_conn_env_key="DBTUNNEL_CLIENT_CONN",
                           client_header_env_key="DBTUNNEL_CLIENT_HEADER",
                           client_header_key="X-API-DBTUNNELTOKEN"
                           ):
        # ensure imports
        self._imports()

        if self._loop is None:
            self._loop = asyncio.new_event_loop()
        else:
            try:
                self._loop.stop()
            except RuntimeError:
                print("Attempting to close existing event loop")
            finally:
                self._loop.close()
                self._loop = asyncio.new_event_loop()


        # subprocess.run(f"kill -9 $(lsof -t -i:{port})", capture_output=True, shell=True)
        random_token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
        client_conn = f"http://0.0.0.0:{port}/secret"
        run_secrets_proxy(self._loop, random_token, port, client_header_key)
        os.environ[secret_env_key] = random_token
        os.environ[client_conn_env_key] = client_conn
        os.environ[client_header_env_key] = client_header_key
        os.environ[env_mode_var] = "true"
        return self

    def run(self):
        self._imports()
        self._run()

    def display(self):
        self._display_html(self._display_url())
