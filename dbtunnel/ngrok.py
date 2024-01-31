import logging
import os

try:
    from pyngrok import ngrok
except ImportError:
    raise ImportError(
        "Please install pyngrok or dbtunnel[ngrok]."
    )

def unsupported_warning(arg):
    if arg is not None:
        print("WARNING: This feature is not supported in ngrok tunnel yet")
    return arg

class NgrokTunnel:

    def __init__(self,

                 port: int,
                 ngrok_tunnel_auth_token: str,
                 ngrok_api_token: str,
                 logger: logging.Logger,
                 basic_auth: str = None,  # "databricks:password"
                 domain: str = None,
                 oauth_provider: str = None,
                 oauth_allow_domains: list[str] = None
                 ):
        self._oauth_allow_domains = unsupported_warning(oauth_allow_domains)
        self._oauth_provider = unsupported_warning(oauth_provider)
        self._domain = unsupported_warning(domain)
        self._basic_auth = unsupported_warning(basic_auth)
        self._ngrok_api_token = ngrok_api_token
        self._ngrok_auth_token = ngrok_tunnel_auth_token
        self._port = port
        self._env = os.environ.copy()
        self._log: logging.Logger = logger

    def _install(self):
        ngrok.install_ngrok()
        ngrok.set_auth_token(self._ngrok_auth_token)

    def run(self):
        self._install()
        listener = ngrok.connect(str(self._port))
        self._log.info(f"Use this information to publicly access your app: \n{listener.public_url}")
        self._log.info("\n\n\n\n")
        return

    def kill_existing_sessions(self):
        # pyngrok doesnt do this so we have to manually do this
        import ngrok
        import requests
        client = ngrok.Client(self._ngrok_api_token)
        for session in client.tunnel_sessions.list():
            session_id = session.id
            self._log.info(f"Killing session: {session_id}")
            stop_session_url = f"https://api.ngrok.com/tunnel_sessions/{session_id}/stop"
            requests.post(stop_session_url, data="{}", headers={
                "Authorization": f"Bearer {self._ngrok_api_token}",
                "Ngrok-Version": "2",
                "Content-Type": "application/json"
            })
