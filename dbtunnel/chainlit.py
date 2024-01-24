import functools
import re
import threading

from dbtunnel.tunnels import DbTunnel, ProxySettings
from dbtunnel.utils import execute, make_asgi_proxy_app


def make_chainlit_local_proxy_config(url_base_path: str, service_host: str = "0.0.0.0",
                                     service_port: int = 9989):
    from dbtunnel.vendor.asgiproxy.config import BaseURLProxyConfigMixin, ProxyConfig
    proxy_root_path = url_base_path

    def _modify_root(content, root_path):
        list_of_uris = [b"/assets", b"/public"]
        for uri in list_of_uris:
            content = content.replace(uri, root_path.encode("utf-8") + uri)
        return content

    def _modify_js_content_root_rewrite(content):
        regex_pattern = r'\{path:"\/",element:(\w+)\.jsx\((\w+),\{\}\)\}'

        decoded_content = content.decode("utf-8")
        # Find all matches
        # find the default root function
        matches = re.findall(regex_pattern, decoded_content)
        if matches:
            print(matches)
            jsx_call = matches[0][0]
            func = matches[0][1]  # Assuming there is only one match

            print(f"Found match: {jsx_call}, {func}")
            modified_code = re.sub(r'\{path:"\*",element:.*\.jsx\(.*,\{replace:!0,to:"\/"\}\)\}',
                                   f'{{path:"*",element:{jsx_call}.jsx({func},{{}})}}', decoded_content)
            return modified_code.encode("utf-8")
        else:
            print("No match found.")
            return content

    def _modify_js_bundle(content, root_path):
        list_of_uris = [b"/project/settings", b"/auth/config", b"/ws/socket.io"]
        for uri in list_of_uris:
            content = content.replace(uri, root_path.encode("utf-8") + uri)
        content = _modify_js_content_root_rewrite(content)
        return content

    def _modify_settings(content, root_path):
        list_of_uris = [b"/public"]
        for uri in list_of_uris:
            content = content.replace(uri, root_path.encode("utf-8") + uri)
        return content

    modify_root = functools.partial(_modify_root, root_path=proxy_root_path)
    modify_js_bundle = functools.partial(_modify_js_bundle, root_path=proxy_root_path)
    modify_settings = functools.partial(_modify_settings, root_path=proxy_root_path)

    config = type(
        "Config",
        (BaseURLProxyConfigMixin, ProxyConfig),
        {
            "upstream_base_url": f"http://{service_host}:{service_port}",
            "rewrite_host_header": f"{service_host}:{service_port}",
            "modify_content": {
                "/": modify_root,
                "": modify_root,
                "*assets/index-*.js": modify_js_bundle,
                "*settings": modify_settings
            }
        },
    )()
    return config


def add_shutdown(app):
    from starlette.responses import JSONResponse
    async def shutdown_app():
        print("Shutting down the app gracefully...")
        # Perform any cleanup or shutdown tasks here
        # ...

        # Shut down the app
        await app.shutdown()

    @app.route("/shutdown", methods=["POST"])
    async def shutdown_endpoint():
        await app.loop.create_task(shutdown_app())
        return JSONResponse({
            "message": "Shutting down!"
        })

    return app


class ChainlitAppTunnel(DbTunnel):

    def _imports(self):
        try:
            import chainlit
            import nest_asyncio
        except ImportError as e:
            print("ImportError: Make sure you have chainlit installed. \n"
                  "pip install chainlit nest_asyncio")
            raise e

    def _run(self):
        import os
        import subprocess

        chainlit_service_port_no_share = 9090
        if self._share is False:
            subprocess.run(f"kill -9 $(lsof -t -i:{chainlit_service_port_no_share})", capture_output=True, shell=True)

            url_base_path = self._proxy_settings.url_base_path
            port = self._port

            # try to shutdown app
            import requests
            try:
                resp = requests.post(f"http://localhost:{port}/shutdown")
                print(resp.text)
            except Exception as e:
                print(e)

            def run_uvicorn_app():
                print("Starting proxy server...")
                app = make_asgi_proxy_app(make_chainlit_local_proxy_config(
                    url_base_path,
                    service_port=chainlit_service_port_no_share
                ))
                app = add_shutdown(app)
                import uvicorn
                uvicorn.run(host="0.0.0.0", port=int(port), app=app, root_path=url_base_path)

            # use process instead of thread to avoid uvicorn error
            import multiprocessing
            uvicorn_process = multiprocessing.get_context('spawn').Process(target=run_uvicorn_app)

            # Start the process
            uvicorn_process.start()
            # uvicorn_thread = threading.Thread(target=run_uvicorn_app)
            # # Start the thread in the background
            # uvicorn_thread.start()

        print("Starting chainlit...", flush=True)

        my_env = os.environ.copy()
        # TODO: fix kernel failure
        # if self._share is True:
        #     subprocess.run(f"kill -9 $(lsof -t -i:{self._port})", capture_output=True, shell=True)

        if self._share is False:
            cmd = ["chainlit", "run", self._chainlit_script_path, "-h", "--host", "0.0.0.0", "--port",
                   f"{chainlit_service_port_no_share}"]
        else:
            cmd = ["chainlit", "run", self._chainlit_script_path, "-h", "--host", "0.0.0.0", "--port", f"{self._port}"]

        print(f"Running command: {' '.join(cmd)}")
        for path in execute(cmd, my_env, cwd=self._cwd):
            print(path, end="")

    def __init__(self, chainlit_script_path: str, cwd: str = None, port: int = 8000):
        super().__init__(port, "chainlit")
        self._chainlit_script_path = chainlit_script_path
        self._cwd = cwd

    def _display_url(self):
        return None
