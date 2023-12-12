import os

try:
    import ngrok as ng
except ImportError:
    raise ImportError(
        "Please install ngrok or dbtunnel[ngrok]."
    )


class NgrokTunnel:

    def __init__(self, port: int,
                 ngrok_tunnel_auth_token: str,
                 ngrok_api_token: str,
                 basic_auth: str = None,  # "databricks:password"
                 domain: str = None,
                 oauth_provider: str = None,
                 oauth_allow_domains: list[str] = None,
                 ):
        self._oauth_allow_domains = oauth_allow_domains
        self._oauth_provider = oauth_provider
        self._domain = domain
        self._basic_auth = basic_auth
        self._ngrok_api_token = ngrok_api_token
        self._ngrok_auth_token = ngrok_tunnel_auth_token
        self._port = port
        self._env = os.environ.copy()


    def run(self):
        os.environ["NGROK_AUTHTOKEN"] = self._ngrok_auth_token
        listener = ng.forward(self._port,
                             domain=self._domain,
                             oauth_provider=self._oauth_provider,
                             oauth_allow_domains=self._oauth_allow_domains,
                             authtoken_from_env=True)
        import asyncio       
        loop = asyncio.get_event_loop()
        loop.run_until_complete(listener)
        print("\n\n\n\n")
        return

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
