from typing import Optional

from starlette.types import Scope

IS_DATABRICKS_PROXY_SCOPE_KEY = "__is_databricks_proxy"


def get_host_from_headers(scope: Scope) -> Optional[str]:
    for header in scope["headers"]:
        key = header[0].decode("utf-8")
        if key.lower() == "host":
            return header[1].decode("utf-8")
    return None


def is_databricks_host(host: str) -> bool:
    # local host is for testing purposes
    return host.endswith(".azuredatabricks.net") or host.endswith(".databricks.com") \
        or host.startswith("0.0.0.0") or host.startswith("127.0.0.1") or host.startswith("localhost")


def add_if_databricks_proxy_scope(scope: Scope) -> None:
    if IS_DATABRICKS_PROXY_SCOPE_KEY in scope:
        return
    host = get_host_from_headers(scope)
    if is_databricks_host(host):
        scope[IS_DATABRICKS_PROXY_SCOPE_KEY] = True


def is_from_databricks_proxy(scope: Scope) -> bool:
    return IS_DATABRICKS_PROXY_SCOPE_KEY in scope and scope[IS_DATABRICKS_PROXY_SCOPE_KEY] is True
