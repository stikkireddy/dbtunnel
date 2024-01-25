import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from fnmatch import fnmatch
from functools import cached_property
from typing import List, Any

try:
    from databricks.sdk import WorkspaceClient
except ImportError:
    print("databricks-sdk not installed. Please install databricks-sdk to use this feature")
    raise


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


def ensure_python_path(env):
    import sys
    import os
    from pathlib import Path
    for python_version_dir in (Path(sys.executable).parent.parent / "lib").iterdir():
        site_packages = str(python_version_dir / "site-packages")
        py_path = env.get("PYTHONPATH", "")
        if site_packages not in py_path.split(":"):
            env["PYTHONPATH"] = f"{py_path}:{site_packages}"


def execute(cmd: List[str], env, cwd=None, ensure_python_site_packages=True):
    if ensure_python_site_packages:
        ensure_python_path(env)
    import subprocess
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True, env=env, cwd=cwd)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


def pkill(process_name):
    try:
        subprocess.run(["pkill", process_name])
        print(f"Processes with name '{process_name}' killed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error killing processes: {e}")


def make_asgi_proxy_app(proxy_config):
    from dbtunnel.vendor.asgiproxy.context import ProxyContext
    from dbtunnel.vendor.asgiproxy.simple_proxy import make_simple_proxy_app

    proxy_context = ProxyContext(proxy_config)
    app = make_simple_proxy_app(proxy_context)
    return app


# from langchain: https://github.com/langchain-ai/langchain/blob/master/libs/langchain/langchain/llms/databricks.py#L86
def get_repl_context() -> Any:
    """Gets the notebook REPL context if running inside a Databricks notebook.
    Returns None otherwise.
    """
    try:
        from dbruntime.databricks_repl_context import get_context

        return get_context()
    except ImportError:
        raise ImportError(
            "Cannot access dbruntime, not running inside a Databricks notebook."
        )


class DatabricksContext:

    def __init__(self):
        self._repl_ctx = get_repl_context()

    @cached_property
    def host(self) -> str:
        return self._repl_ctx.browserHostName

    @cached_property
    def token(self) -> str:
        return self._repl_ctx.apiToken

    @cached_property
    def current_user_name(self) -> str:
        return WorkspaceClient(host=self.host,
                               token=self.token).current_user.me().user_name


@dataclass
class WarehouseDetails:
    hostname: str
    http_path: str
    name: str
    serverless: bool


class ComputeUtils:

    def __init__(self, dbx_ctx: DatabricksContext):
        self._ctx = dbx_ctx
        self._client = WorkspaceClient(host=self._ctx.host, token=self._ctx.token)

    def get_warehouse(self, name_glob: str, ignore_case: bool = True, serverless_only: bool = True):
        for warehouse in self._client.warehouses.list():
            if serverless_only is True and warehouse.enable_serverless_compute is False:
                continue  # Skip warehouses that do not have serverless compute enabled

            if ignore_case is True:
                name_match = fnmatch(warehouse.name.lower(), name_glob.lower())
            else:
                name_match = fnmatch(warehouse.name, name_glob)

            if name_match is False:
                continue  # Skip warehouses that do not match the name_glob

            hostname = warehouse.odbc_params.hostname
            http_path = warehouse.odbc_params.path
            return WarehouseDetails(hostname,
                                    http_path,
                                    warehouse.name,
                                    warehouse.enable_serverless_compute)


ctx = DatabricksContext()
compute_utils = ComputeUtils(ctx)
