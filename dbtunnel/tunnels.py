import abc
import datetime
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Literal, Optional
from urllib.parse import urlparse

from dbtunnel.utils import pkill, ctx, get_logger


@dataclass
class ProxySettings:
    proxy_url: str
    port: str
    url_base_path: str
    url_base_path_no_port: Optional[str] = None

    def get_proxy_url(self, ensure_ends_with_slash=False):
        """
        For certain apps that use relative paths like "assets/index-*.js" we need to ensure that the url ends
        with a slash.
        """
        if ensure_ends_with_slash is True:
            return self.proxy_url.rstrip("/") + "/"
        return self.proxy_url


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
    url_base_path_no_port = f"/driver-proxy/o/{org_id}/{cluster_id}"
    url_base_path = f"{url_base_path_no_port}/{port}/"
    return ProxySettings(
        proxy_url=f"{prefix_url_settings[cloud_norm]}{org_id}{org_shard}.{suffix_url_settings[cloud_norm]}{url_base_path}",
        port=str(port),
        url_base_path=url_base_path,
        url_base_path_no_port=url_base_path_no_port
    )


Flavor = Literal[
    "gradio", "fastapi", "nicegui", "streamlit", "stable-diffusion-ui", "bokeh", "flask", "dash", "solara",
    "code-server", "chainlit", "shiny-python"]


def get_current_username() -> str:
    return ctx.current_user_name


def extract_hostname(url):
    parsed_url = urlparse(url)
    return parsed_url.hostname


def ensure_scheme(url):
    if not url.startswith("http") and not url.startswith("https"):
        return f"https://{url}"


# TODO: Make the with commands lazy so the logger and other
#  init methods are executed first before the with commands

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
        self._share = False
        self._share_information = None
        self._share_trigger_callback = None
        self._log: logging.Logger = get_logger()  # initialize logger during the run method
        self._basic_tunnel_auth = {"simple_auth": False, "simple_auth_workspace_url": None}

    @abc.abstractmethod
    def _imports(self):
        pass

    @abc.abstractmethod
    def _run(self):
        pass

    @abc.abstractmethod
    def _display_url(self):
        pass

    @property
    def shared(self):
        return self._share

    def inject_auth(self, host: str = None, token: str = None):
        if os.getenv("DATABRICKS_HOST") is None:
            self._log.info("Setting databricks host from context")
            os.environ["DATABRICKS_HOST"] = host or ensure_scheme(ctx.host)
        if os.getenv("DATABRICKS_TOKEN") is None:
            self._log.info("Setting databricks token from context")
            os.environ["DATABRICKS_TOKEN"] = token or ctx.token

        return self

    def inject_sql_warehouse(self, http_path: str, server_hostname: str = None, token: str = None):
        if os.getenv("DATABRICKS_SERVER_HOSTNAME") is None:
            self._log.info("Setting databricks server hostname from context")
            os.environ["DATABRICKS_SERVER_HOSTNAME"] = server_hostname or extract_hostname(
                ctx.host)

        if os.getenv("DATABRICKS_TOKEN") is None:
            self._log.info("Setting databricks token from context")
            os.environ["DATABRICKS_TOKEN"] = token or ctx.token

        if os.getenv("DATABRICKS_HTTP_PATH") is None:
            self._log.info("Setting databricks warehouse http path")
            os.environ["DATABRICKS_HTTP_PATH"] = http_path

        return self

    def inject_env(self, **kwargs):
        for k, v in kwargs.items():
            if type(v) != str:
                raise ValueError(f"Value for environment variable {k} must be a string")
            self._log.info(f"Setting environment variable {k}")
            os.environ[k] = v
        return self

    def with_token_auth(self):
        self._basic_tunnel_auth["token_auth"] = True
        self._basic_tunnel_auth["token_auth_workspace_url"] = ctx.host
        return self

    def with_custom_logger(self, *,
                           logger: Optional[logging.Logger] = None,
                           app_name: str = "dbtunnel",
                           cluster_logging_file_path: Optional[Path] = None,
                           logging_archive_folder: Optional[Path] = None,
                           rotate_when: Literal["S", "M", "H", "D", "midnight"] = "H",
                           rotate_interval: int = 1,
                           backup_count: int = 3,
                           at_time: Optional[datetime.time] = None,
                           format_str: str = "[%(asctime)s] [%(levelname)s] {%(module)s.py:%(funcName)s:%(lineno)d} - %(message)s",
                           datefmt_str: str = "%Y-%m-%dT%H:%M:%S%z"
                           ):
        if logger is not None:
            self._log = logger
            return self
        self._log = get_logger(app_name=app_name,
                               cluster_logging_file_path=cluster_logging_file_path,
                               logging_archive_folder=logging_archive_folder,
                               rotate_when=rotate_when,
                               rotate_interval=rotate_interval,
                               backup_count=backup_count,
                               at_time=at_time,
                               format_str=format_str,
                               datefmt_str=datefmt_str)
        return self

    def run(self):
        """
        Lifecycle:
        1. initialize logger
        2. import libraries and return error immediately if things are not installed
        3. Then spawn processes.
        :return:
        """
        self._imports()
        if self._share is True and self._share_trigger_callback is not None:
            import nest_asyncio
            nest_asyncio.apply()
            self._share_trigger_callback()
        if self._share is True and self._share_information is not None:
            self._log.info(f"Use this information to publicly access your app: \n{self._share_information.public_url}")
        self._run()

    # right now only ngrok is supported so auth token is required field but in future there may be devtunnels
    def share_to_internet_via_ngrok(self,
                                    *,
                                    ngrok_api_token: str,
                                    ngrok_tunnel_auth_token: str,
                                    kill_existing_processes: bool = True,
                                    kill_all_tunnel_sessions: bool = False,
                                    basic_auth: str = None,  # "databricks:password"
                                    domain: str = None,
                                    oauth_provider: str = None,
                                    oauth_allow_domains: list[str] = None):
        self._share = True
        if kill_existing_processes is True:
            try:
                pkill("ngrok")
            except KeyError:
                self._log.error("no running tunnels to kill")
        from dbtunnel.ngrok import NgrokTunnel
        ngrok_tunnel = NgrokTunnel(self._port,
                                   ngrok_tunnel_auth_token,
                                   ngrok_api_token,
                                   self._log,
                                   basic_auth=basic_auth,
                                   domain=domain,
                                   oauth_provider=oauth_provider,
                                   oauth_allow_domains=oauth_allow_domains)

        def ngrok_callback():
            if kill_all_tunnel_sessions is True:
                ngrok_tunnel.kill_existing_sessions()
            ngrok_tunnel.run()

        self._share_trigger_callback = ngrok_callback

        return self

    def display(self):
        pass  # no op because of the annoying flickering
        # self._display_html(self._display_url())
