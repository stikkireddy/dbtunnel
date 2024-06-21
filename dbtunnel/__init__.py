import subprocess

from dbtunnel.utils import ctx, compute_utils


class AppTunnels:
    """
    This class is used to create tunnels to different apps. It is the user facing api should not have breaking changes.
    """

    @staticmethod
    def kill_port(port: int):
        subprocess.run(f"kill -9 $(lsof -t -i:{port})", capture_output=True, shell=True)

    @staticmethod
    def fastapi(app, port: int = 8080):
        from dbtunnel.fastapi import FastApiAppTunnel
        return FastApiAppTunnel(app, port)

    @staticmethod
    def gradio(app=None,
               path: str = None,
               cwd: str = None,
               port: int = 8080):
        if app is None and path is None:
            raise ValueError("Either gradio app object or path must be provided")
        from dbtunnel.gradio import GradioAppTunnel
        return GradioAppTunnel(app, path, cwd, port)

    @staticmethod
    def nicegui(app, storage_secret: str = "", port: int = 8080):
        from dbtunnel.nicegui import NiceGuiAppTunnel
        return NiceGuiAppTunnel(app, storage_secret, port)

    @staticmethod
    def streamlit(path, port: int = 8080):
        from dbtunnel.streamlit import StreamlitTunnel
        return StreamlitTunnel(path, port)

    @staticmethod
    def stable_diffusion_ui(no_gpu: bool, port: int = 7860, enable_insecure_extensions: bool = False,
                            extra_flags: str = ""):
        # todo auto detect with torch
        from dbtunnel.stable_diffusion_ui import StableDiffusionUITunnel
        return StableDiffusionUITunnel(no_gpu, port, enable_insecure_extensions, extra_flags)

    @staticmethod
    def bokeh(path, port: int = 8080):
        from dbtunnel.bokeh import BokehTunnel
        return BokehTunnel(path, port)

    @staticmethod
    def flask(app, port: int = 8080):
        from dbtunnel.flask import FlaskAppTunnel
        return FlaskAppTunnel(app, port)

    @staticmethod
    def dash(app, port: int = 8080):
        from dbtunnel.dash import DashAppTunnel
        return DashAppTunnel(app, port)

    @staticmethod
    def solara(path, port: int = 8080):
        from dbtunnel.solara import SolaraAppTunnel
        return SolaraAppTunnel(path, port)

    @staticmethod
    def code_server(directory_path: str = None, repo_name: str = None, port: int = 9988,
                    extension_ids: list[str] = None):
        from dbtunnel.code_server import CodeServerTunnel
        return CodeServerTunnel(directory_path, repo_name, port, extension_ids)

    @staticmethod
    def chainlit(script_path: str, cwd: str = None, port: int = 8000):
        from dbtunnel.chainlit import ChainlitAppTunnel
        return ChainlitAppTunnel(script_path, cwd=cwd, port=port)

    @staticmethod
    def shiny_python(app, port: int = 8080):
        from dbtunnel.shiny import ShinyPythonAppTunnel
        return ShinyPythonAppTunnel(app, port)

    @staticmethod
    def uvicorn(app, port: int = 8080):
        from dbtunnel.uvicorn import UvicornAppTunnel
        return UvicornAppTunnel(app, port)

    @staticmethod
    def arize_phoenix(port: int = 9098):
        from dbtunnel.arize_phoenix_ui import ArizePhoenixUITunnel
        return ArizePhoenixUITunnel(port)

    @staticmethod
    def ray(app, port: int = 8080):
        from dbtunnel.ray import RayAppTunnel
        return RayAppTunnel(app, port)
    

dbtunnel = AppTunnels()
