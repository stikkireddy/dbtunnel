import atexit
import datetime
import logging
import os
import queue
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from fnmatch import fnmatch
from functools import cached_property
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import List, Any, Optional, Literal

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
    from pathlib import Path
    for python_version_dir in (Path(sys.executable).parent.parent / "lib").iterdir():
        site_packages = str(python_version_dir / "site-packages")
        py_path = env.get("PYTHONPATH", "")
        if site_packages not in py_path.split(":"):
            env["PYTHONPATH"] = f"{py_path}:{site_packages}"


def execute(cmd: List[str], env, cwd=None, ensure_python_site_packages=True, shell=False, trim_new_line=True):
    if ensure_python_site_packages:
        ensure_python_path(env)
    import subprocess
    if shell is True:
        cmd = " ".join(cmd)
    popen = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=True,
                             shell=shell,
                             env=env,
                             cwd=cwd,
                             bufsize=1)
    if popen.stdout is not None:
        for stdout_line in iter(popen.stdout.readline, ""):
            if trim_new_line:
                stdout_line = stdout_line.strip()
            yield stdout_line

    # if popen.stderr is not None:
    #     for stderr_line in iter(popen.stderr.readline, ""):  # Iterate over stderr
    #         yield stderr_line

    popen.stdout.close()
    # popen.stderr.close()  # Close stderr
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


def pkill(process_name):
    try:
        subprocess.run(["pkill", process_name])
        print(f"Processes with name '{process_name}' killed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error killing processes: {e}")

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


def get_workspace_host_via_spark_config() -> Optional[str]:
    try:
        from pyspark.sql import SparkSession

        # databricks notebook and jobs will already have spark sessions
        spark = SparkSession.getActiveSession()
        return spark.conf.get("spark.databricks.workspaceUrl")
    except Exception:
        print("Not running inside a Databricks notebook or job, unable to get workspace url from spark session.")
        return None


class DatabricksContext:

    def __init__(self):
        self._repl_ctx = get_repl_context()

    @cached_property
    def host(self) -> str:
        if hasattr(self._repl_ctx, "browserHostName"):
            return self._repl_ctx.browserHostName
        spark_conf_ws_url = get_workspace_host_via_spark_config()
        if spark_conf_ws_url is not None:
            return spark_conf_ws_url
        raise ValueError("Unable to get workspace host from REPL context or spark config")

    @cached_property
    def token(self) -> str:
        if hasattr(self._repl_ctx, "apiToken"):
            return self._repl_ctx.apiToken
        raise ValueError("Unable to get token from REPL context")

    @cached_property
    def current_user_name(self) -> str:
        return WorkspaceClient(host=self.host,
                               token=self.token).current_user.me().user_name

    @cached_property
    def current_username_alphanumeric(self) -> str:
        sanitized = self.current_user_name.split("@")[0].replace(".", "-")
        return "".join(c for c in sanitized if c.isalnum() or c == "-")


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


class ArchivingTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Rotate the files in the cluster native FS and during the rotate time period copy the file to
    a volume so there are no issues with file system shenanigans with FUSE implementation
    """

    def __init__(self, archive_path: Path, filename, when='h', interval=1, backupCount=0,
                 encoding=None, delay=False, utc=False, atTime=None,
                 errors=None):
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime, errors)
        self._archive_path = archive_path
        if not self._archive_path.exists():
            self._archive_path.mkdir(parents=True)

    def rotate(self, source, dest):
        super().rotate(source, dest)
        # copy dest file to archive path
        self.archive_log_file(dest)

    def archive_log_file(self, log_file):
        try:
            shutil.copy(log_file, str(self._archive_path))
        except Exception as e:
            print(f"Unable to archive log file: {e}")


def get_logger(
        *,
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
    # driver instead of workspace path to not deal with WSFS
    home_dir = os.path.expanduser('~')
    cluster_logging_file_path = cluster_logging_file_path or Path(f"{home_dir}/logs/{app_name}/{app_name}.log")
    if not cluster_logging_file_path.parent.exists():
        cluster_logging_file_path.parent.mkdir(parents=True)

    logger = logging.getLogger(app_name)

    # Create a queue
    log_queue = queue.Queue(maxsize=100)

    # Create a formatter for 'simple' and 'detailed' formats
    detailed_formatter = logging.Formatter(
        format_str,
        datefmt=datefmt_str
    )

    # Create a StreamHandler for 'stderr' with 'simple' formatter
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(detailed_formatter)

    # Create a RotatingFileHandler for 'file' with 'detailed' formatter
    time_rotate_cfg = {
        "when": rotate_when,
        "interval": rotate_interval,
        "backupCount": backup_count,
        "atTime": at_time,
    }
    if logging_archive_folder is not None and logging_archive_folder.exists():
        file_handler = ArchivingTimedRotatingFileHandler(
            archive_path=logging_archive_folder,
            filename=cluster_logging_file_path,
            **time_rotate_cfg
        )
    else:
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=cluster_logging_file_path,
            **time_rotate_cfg
        )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)

    # Create a QueueListener with the created queue and the added handlers
    queue_handler = logging.handlers.QueueHandler(log_queue)

    queue_listener = logging.handlers.QueueListener(
        log_queue, stdout_handler, file_handler, respect_handler_level=True
    )

    # incase this is reinitialized remove all handlers
    for handler in logger.handlers:
        logger.removeHandler(handler)

    # Add the QueueListener handler to the root logger
    logger.addHandler(queue_handler)

    # Set the log level for the root logger
    logger.setLevel(logging.DEBUG)

    # disable py4j logger
    logging.getLogger("py4j").setLevel(logging.ERROR)

    # Start the QueueListener
    queue_listener.start()

    # Register a function to stop the QueueListener on program exit
    atexit.register(queue_listener.stop)

    return logger


try:
    ctx = DatabricksContext()
    compute_utils = ComputeUtils(ctx)
except Exception as e:
    logging.info("Unable to establish context, you are most likely running outside of databricks")
    ctx = None
    compute_utils = None
