import os

try:
    from pyngrok import ngrok
except ImportError:
    raise ImportError(
        "Please install pyngrok or dbtunnel[ngrok]."
    )


class NgrokTunnel:

    def __init__(self, port: int, ngrok_auth_token: str):
        self._ngrok_auth_toke = ngrok_auth_token
        self._port = port
        self._env = os.environ.copy()

    def _setup(self):
        ngrok.install_ngrok()
        ngrok.set_auth_token(self._ngrok_auth_toke)

    def run(self):
        self._setup()
        return ngrok.connect(str(self._port))
