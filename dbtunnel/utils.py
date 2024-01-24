import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from typing import List


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
