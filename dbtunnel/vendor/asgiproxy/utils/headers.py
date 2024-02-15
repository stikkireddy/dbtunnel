from typing import Optional, Iterator

from starlette.types import Scope

from dbtunnel.vendor.asgiproxy.frameworks import Frameworks

IS_DATABRICKS_PROXY_SCOPE_KEY = "__is_databricks_proxy"


def get_hosts_from_headers(scope: Scope) -> Iterator[str]:
    for header in scope["headers"]:
        key = header[0].decode("utf-8")
        if key.lower() == "host":
            yield header[1].decode("utf-8")
        if key.lower() == "x-forwarded-host":
            yield header[1].decode("utf-8")
    return

def get_forwarded_host_from_headers(scope: Scope) -> Optional[str]:
    for header in scope["headers"]:
        key = header[0].decode("utf-8")
        if key.lower() == "x-forwarded-host":
            return header[1].decode("utf-8")
    return None


def is_databricks_host(host: str) -> bool:
    # local host is for testing purposes
    return host.endswith(".azuredatabricks.net") or host.endswith(".databricks.com") \
        or host.startswith("0.0.0.0") or host.startswith("127.0.0.1") or host.startswith("localhost")


def add_if_databricks_proxy_scope(scope: Scope) -> None:
    if IS_DATABRICKS_PROXY_SCOPE_KEY in scope:
        return
    hosts = get_hosts_from_headers(scope)
    if any(is_databricks_host(host) for host in hosts) is True:
        scope[IS_DATABRICKS_PROXY_SCOPE_KEY] = True


def is_from_databricks_proxy(scope: Scope) -> bool:
    return IS_DATABRICKS_PROXY_SCOPE_KEY in scope and scope[IS_DATABRICKS_PROXY_SCOPE_KEY] is True


FRAMEWORK_KEY = "__framework"
PROXY_PORT = "__proxy_port"

def add_framework_to_scope(scope: Scope, framework: str) -> None:
    scope[FRAMEWORK_KEY] = framework
    return

def add_origin_port_to_scope(scope: Scope, port: int) -> None:
    scope[PROXY_PORT] = str(port)
    return


def get_origin_port_from_scope(scope: Scope):
    return scope.get(PROXY_PORT)

def is_streamlit(scope: Scope) -> bool:
    return Frameworks.STREAMLIT == scope.get(FRAMEWORK_KEY, None)