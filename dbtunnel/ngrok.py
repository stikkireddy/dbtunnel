import os

try:
    from pyngrok import ngrok
except ImportError:
    raise ImportError(
        "Please install pyngrok or dbtunnel[ngrok]."
    )


class NgrokTunnel:

    def __init__(self, port: int, ngrok_tunnel_auth_token: str, ngrok_api_token: str):
        self._ngrok_api_token = ngrok_api_token
        self._ngrok_auth_token = ngrok_tunnel_auth_token
        self._port = port
        self._env = os.environ.copy()

    def _setup(self):
        ngrok.install_ngrok()
        ngrok.set_auth_token(self._ngrok_auth_token)

    def run(self):
        self._setup()
        return ngrok.connect(str(self._port))

    def kill_existing_sessions(self):
        # pyngrok doesnt do this so we have to manually do this
        import requests
        list_sessions_url = "https://api.ngrok.com/tunnel_sessions"
        tunnel_sessions = requests.get(list_sessions_url, headers={
            "Authorization": f"Bearer {self._ngrok_api_token}",
            "Ngrok-Version": "2"
        }).json()
        sessions = tunnel_sessions["tunnel_sessions"]
        for session in sessions:
            session_id = session["id"]
            print(f"Killing session: {session_id}")
            stop_session_url = f"https://api.ngrok.com/tunnel_sessions/{session_id}/stop"
            import requests
            requests.post(stop_session_url, data="{}", headers={
                "Authorization": f"Bearer {self._ngrok_api_token}",
                "Ngrok-Version": "2",
                "Content-Type": "application/json"
            })
