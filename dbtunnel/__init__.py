import abc
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal, Dict, Any


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


class FastApiAppTunnel(DbTunnel):

    def __init__(self, fastapi_app, port: int = 8080):
        super().__init__(port, flavor="fastapi")
        self._fastapi_app = fastapi_app

    def _imports(self):
        try:
            from fastapi import FastAPI
            import uvicorn
            import nest_asyncio
        except ImportError as e:
            print("ImportError: Make sure you have fastapi, nest_asyncio and uvicorn installed;"
                  "pip install fastapi nest_asyncio uvicorn")
            raise e

    def _run(self):
        self.display()
        print("Starting server...", flush=True)
        from fastapi import FastAPI
        import uvicorn
        app = FastAPI(root_path=self._proxy_settings.url_base_path.rstrip("/"))
        app.mount("/", self._fastapi_app)
        import nest_asyncio
        nest_asyncio.apply()

        # uvicorn.run(app, host="0.0.0.0", port=self._port)
        # Start the server
        async def start():
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=self._port,
            )
            server = uvicorn.Server(config)
            await server.serve()

        # Run the asyncio event loop instead of uvloop to enable re entrance
        import asyncio
        print(f"Use this link: \n{self._proxy_settings.proxy_url}")
        asyncio.run(start())

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'


class GradioAppTunnel(DbTunnel):

    def __init__(self, gradio_app, port: int = 8080):
        super().__init__(port, flavor="gradio")
        self._gradio_app = gradio_app

    def _imports(self):
        try:
            from fastapi import FastAPI
            import uvicorn
            import gradio as gr
            import nest_asyncio
        except ImportError as e:
            print("ImportError: Make sure you have fastapi, nest_asyncio uvicorn, gradio installed. \n"
                  "pip install fastapi nest_asyncio uvicorn gradio")
            raise e

    def _run(self):
        self.display()
        print("Starting server...", flush=True)
        from fastapi import FastAPI
        import uvicorn
        import gradio as gr
        app = FastAPI(root_path=self._proxy_settings.url_base_path.rstrip("/"))
        app = gr.mount_gradio_app(app, self._gradio_app, path="/")
        import nest_asyncio
        nest_asyncio.apply()

        # Start the server
        async def start():
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=self._port,
            )
            server = uvicorn.Server(config)
            await server.serve()

        # Run the asyncio event loop instead of uvloop to enable re entrance
        import asyncio
        print(f"Use this link: \n{self._proxy_settings.proxy_url}")
        asyncio.run(start())

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'


class NiceGuiAppTunnel(DbTunnel):

    def __init__(self, ui, storage_secret: str = "", port: int = 8080):
        super().__init__(port, flavor="nicegui")
        self._nicegui_app = ui
        self._storage_secret = storage_secret

    def _imports(self):
        try:
            from fastapi import FastAPI
            import uvicorn
            import nicegui
            import nest_asyncio
        except ImportError as e:
            print("ImportError: Make sure you have fastapi, nest_asyncio uvicorn, gradio installed. \n"
                  "pip install fastapi nest_asyncio uvicorn gradio")
            raise e

    def _run(self):
        self.display()
        print("Starting server...", flush=True)
        from fastapi import FastAPI
        import uvicorn
        app = FastAPI(root_path=self._proxy_settings.url_base_path.rstrip("/"))
        self._nicegui_app.run_with(
            app,
            storage_secret=self._storage_secret,
        )

        import nest_asyncio
        nest_asyncio.apply()

        # Start the server
        async def start():
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=self._port,
            )
            server = uvicorn.Server(config)
            await server.serve()

        # Run the asyncio event loop instead of uvloop to enable re entrance
        import asyncio
        print(f"Use this link: \n{self._proxy_settings.proxy_url}")
        asyncio.run(start())

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'


def streamlit_patch_websockets_v2():
    from pathlib import Path
    import subprocess
    import streamlit
    p = Path(streamlit.__file__)
    _dir = (p.parent)
    process = subprocess.run(f"find {_dir} -type f -exec sed -i -e 's/\"stream\"/\"ws\"/g' {{}} \;",
                             capture_output=True, shell=True)
    return process.stdout.decode()


class StreamlitTunnel(DbTunnel):

    def __init__(self, script_path: str, port: int):
        super().__init__(port, "streamlit")
        self._script_path = script_path

    def _imports(self):
        try:
            import streamlit
            import nest_asyncio
        except ImportError as e:
            print("ImportError: Make sure you have nest_asyncio, streamlit installed. \n"
                  "pip install nest_asyncio streamlit")
            raise e

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'

    def _run(self):
        self.display()
        print("Starting server...", flush=True)
        import nest_asyncio
        nest_asyncio.apply()
        streamlit_patch_websockets_v2()
        print(f"Use this link: \n{self._proxy_settings.proxy_url}")
        with process_file(self._script_path) as file_path:
            self.run_streamlit(file_path, self._port)

    @staticmethod
    def run_streamlit(path, port):
        import os
        import subprocess
        my_env = os.environ.copy()
        my_env["STREAMLIT_SERVER_PORT"] = f"{port}"
        my_env["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
        my_env["STREAMLIT_SERVER_HEADLESS"] = "true"
        subprocess.run(f"kill -9 $(lsof -t -i:{port})", capture_output=True, shell=True)

        print(f"Deploying streamlit app at path: {path} on port: {port}")
        cmd = ["streamlit",
               "run",
               path,
               "--browser.gatherUsageStats",
               "false"]
        print(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env):
            print(path, end="")


class StableDiffusionUITunnel(DbTunnel):

    def __init__(self, no_gpu: bool, port: int):
        super().__init__(port, "stable-diffusion-ui")
        self._no_gpu = no_gpu

    def _imports(self):
        try:
            import streamlit
            import nest_asyncio
        except ImportError as e:
            print("ImportError: Make sure you have nest_asyncio, streamlit installed. \n"
                  "pip install nest_asyncio streamlit")
            raise e

    def _display_url(self):
        # must end with a "/" for it to not redirect
        return f'<a href="{self._proxy_settings.proxy_url}">Click to go to {self._flavor} App!</a>'

    def _run(self):
        self.display()
        print("Starting server...", flush=True)
        import nest_asyncio
        import requests
        import os
        nest_asyncio.apply()
        script_url = "https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui/master/webui.sh"

        # Download the script
        response = requests.get(script_url)
        script_content = response.text

        # Create a temporary file to save the script
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as script_file:
            script_file.write(script_content)
            script_path = script_file.name

        # Set environment variable
        if self._no_gpu:
            os.environ["COMMANDLINE_ARGS"] = (
                f"--subpath={self._proxy_settings.url_base_path.rstrip('/').lstrip('/')} --skip"
                f"-torch-cuda-test")
        else:
            os.environ["COMMANDLINE_ARGS"] = f"--subpath={self._proxy_settings.url_base_path.rstrip('/').lstrip('/')}"

        import os
        import subprocess
        my_env = os.environ.copy()
        subprocess.run(f"kill -9 $(lsof -t -i:{self._port})", capture_output=True, shell=True)

        print(f"Deploying stable diffusion web ui app at path: \n{self._proxy_settings.proxy_url}")
        cmd = ["bash", script_path, "-f", "--listen"]
        print(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env):
            print(path, end="")


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
