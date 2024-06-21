import abc
import datetime
import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Literal, Optional
from urllib.parse import urlparse

from databricks.sdk import WorkspaceClient

from dbtunnel.utils import pkill, ctx, get_logger, execute


class DBTunnelError(Exception):
    pass


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


def remove_lowest_subdomain_from_host(url):
    parsed_url = urlparse(url)
    host = parsed_url.netloc if parsed_url.netloc else parsed_url.path
    parts = host.split('.')
    # Check if there are subdomains to remove
    if len(parts) > 2:
        # Remove the lowest subdomain
        parts.pop(0)

    # Reconstruct the modified host
    modified_host = '.'.join(parts)

    return modified_host


def get_cloud_proxy_settings(cloud: str, org_id: str, cluster_id: str, port: int) -> ProxySettings:
    cloud_norm = cloud.lower()
    if cloud_norm not in ["aws", "azure"]:
        raise Exception("only supported in aws or azure")
    prefix_url_settings = {
        "aws": "https://dbc-dp-",
        "azure": "https://adb-dp-",
    }
    suffix_url_settings = {
        "azure": "azuredatabricks.net",
    }
    if cloud_norm == "aws":
        suffix = remove_lowest_subdomain_from_host(ctx.host)
        suffix_url_settings["aws"] = suffix

    org_shard = ""
    # org_shard doesnt need a suffix of "." for dnsname its handled in building the url
    # only azure right now does dns sharding
    # gcp will need this
    if cloud_norm == "azure":
        org_shard_id = int(org_id) % 20
        org_shard = f".{org_shard_id}"

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
    "code-server", "chainlit", "shiny-python", "uvicorn", "arize-phoenix", "ray"]


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
        self._basic_tunnel_auth = {"token_auth": False, "token_auth_workspace_url": None}

    def _is_single_user_cluster(self):
        ws = WorkspaceClient()
        cluster = ws.clusters.get(self._cluster_id)
        from databricks.sdk.service.compute import DataSecurityMode
        return (cluster.data_security_mode in [DataSecurityMode.SINGLE_USER, DataSecurityMode.LEGACY_SINGLE_USER]) \
            and cluster.single_user_name == get_current_username()

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

    def ui_url(self):
        self._display_html(f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>')

    def inject_auth(self, host: str = None, token: str = None, write_cfg: bool = False):
        """
        Inject databricks host and token into the environment

        :param host: any databricks url you may want to use, otherwise defaults to your notebook session host
        :param token: any databricks token you may want to use, otherwise defaults to your notebook session token
        :param write_cfg: this will create a .databrickscfg file in the root directory, only works on single user clusters.
        """
        if os.getenv("DATABRICKS_HOST") is None:
            self._log.info("Setting databricks host from context")
            os.environ["DATABRICKS_HOST"] = host or ensure_scheme(ctx.host)
        if os.getenv("DATABRICKS_TOKEN") is None:
            self._log.info("Setting databricks token from context")
            os.environ["DATABRICKS_TOKEN"] = token or ctx.token

        if write_cfg is True and self._is_single_user_cluster():
            expanded_file_path = os.path.expanduser("~/.databrickscfg")
            with open(expanded_file_path, "w") as f:
                f.write(f"[DEFAULT]\nhost = {os.getenv('DATABRICKS_HOST')}\ntoken = {os.getenv('DATABRICKS_TOKEN')}\n")

        return self

    def inject_sql_warehouse(self, http_path: str, server_hostname: str = None, token: str = None):
        """
        Inject databricks warehouse http path into the environment and auth
        :param http_path: the http path to the warehouse
        :param server_hostname: the hostname of the databricks workspace, defaults to the current workspace where the notebook is running
        :param token: any databricks token you may want to use, otherwise defaults to your notebook session token
        :return:
        """
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
        """
        Inject environment variables into the environment. Keep in mind environment variables are case sensitive

        Example usage:
        dbtunnel.chainlit("path/to/script").inject_env(ENV_VAR1="value1", ENV_VAR2="value2").run()

        :param kwargs: keyword arguments for the environment variables you want to set
        :return:
        """
        for k, v in kwargs.items():
            if type(v) != str:
                raise ValueError(f"Value for environment variable {k} must be a string")
            self._log.info(f"Setting environment variable {k}")
            os.environ[k] = v
        return self

    def with_token_auth(self):
        """
        Experimental feature do not use.
        :return:
        """

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

    def _validate_options(self):
        if self._share is True and self._basic_tunnel_auth["token_auth"] is True:
            raise DBTunnelError("Cannot use token auth with shared tunnel; remove token auth or remove sharing")

    def run(self):
        """
        Lifecycle:
        1. initialize logger
        2. import libraries and return error immediately if things are not installed
        3. Then spawn processes.
        :return:
        """
        self._imports()
        self._validate_options()
        if self._share is True and self._share_trigger_callback is not None:
            import nest_asyncio
            nest_asyncio.apply()
            self._share_trigger_callback()
        if self._share is True and self._share_information is not None:
            self._log.info(f"Use this information to publicly access your app: \n{self._share_information.public_url}")
        self._run()

    def share_to_internet(self,
                          *,
                          app_name: str,
                          tunnel_host: str,
                          app_host: str,
                          tunnel_port: int = 7000,
                          subdomain: str = None,
                          sso: bool = False):
        self._share = True
        from dbtunnel.relay import DBTunnelRelayClient
        dbtunnel_relay_client = DBTunnelRelayClient(
            app_name=app_name,
            app_host=app_host,
            tunnel_host=tunnel_host,
            tunnel_port=tunnel_port,
            local_port=self._port,
            subdomain=subdomain,
            sso=sso,
            user=ctx.current_user_name
        )
        print("Downloading required binary if it does not exist!")
        dbtunnel_relay_client.download_on_linux()

        def share_to_internet():
            try:
                print("Access your app at: ", dbtunnel_relay_client.public_url())
                dbtunnel_relay_client.run_as_thread(output_func=self._log.info)
            except Exception as e:
                self._log.error(e)

        self._share_trigger_callback = share_to_internet
        return self

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


class DbTunnelProxy:

    def __init__(self,
                 proxy_port: int,
                 service_port: int,
                 url_base_path: str,
                 framework: str,
                 token_auth: bool = False,
                 token_auth_workspace_url: Optional[str] = None,
                 cwd: str = None):
        self._proxy_port = proxy_port
        self._service_port = service_port
        self._url_base_path = url_base_path
        self._framework = framework
        self._token_auth = token_auth
        self._token_auth_workspace_url = token_auth_workspace_url
        self._cwd = cwd
        self._log: logging.Logger = get_logger(app_name="dbtunnel-proxy")
        self._thread = self._make_thread()

    def _make_thread(self):
        my_env = os.environ.copy()

        def run_uvicorn_app(env_copy):
            proxy_cmd = ["python", "-m", "dbtunnel.vendor.asgiproxy",
                         "--port", str(self._proxy_port),
                         "--service-port", str(self._service_port),
                         "--url-base-path", self._url_base_path,
                         "--framework", self._framework]
            if self._token_auth is True:
                proxy_cmd.append("--token-auth")
            if self._token_auth_workspace_url is not None:
                proxy_cmd.append("--token-auth-workspace-url")
                proxy_cmd.append(self._token_auth_workspace_url)

            self._log.info(f"Running proxy server via command: {' '.join(proxy_cmd)}")
            try:
                for log_stmt in execute(proxy_cmd, env_copy, cwd=self._cwd):
                    self._log.info(log_stmt.rstrip("\n"))
            except Exception as e:
                self._log.info("Error running proxy server")

        return threading.Thread(target=run_uvicorn_app, args=(my_env,))

    def start(self):
        self._thread.start()
        return self

    def wait(self):
        self._thread.join()
        return self
