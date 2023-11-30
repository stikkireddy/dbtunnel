import os
import shutil
import tempfile
from contextlib import contextmanager


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


def run_secrets_proxy(required_token: str, proxy_port=9898, token_key: str = "X-API-DBTUNNELTOKEN"):
    from fastapi import FastAPI
    import uvicorn

    from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
    from starlette.requests import Request
    from starlette.responses import Response, JSONResponse
    class TunnelTokenAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(
                self, request: Request, call_next: RequestResponseEndpoint
        ) -> Response:
            header_token = request.headers.get(token_key)

            if header_token is None or header_token != required_token:
                return JSONResponse(
                    status_code=401,
                    content={"message": f"Unauthorized wrong token. Make sure {token_key} is set correctly"},
                )
                # raise HTTPException(status_code=401, detail="Unauthorized")

            response = await call_next(request)
            return response

    app = FastAPI()
    app.add_middleware(TunnelTokenAuthMiddleware)

    @app.get("/secret")
    async def root():
        return {"message": "Hello World"}

    # import nest_asyncio
    # nest_asyncio.apply()

    # uvicorn.run(app, host="0.0.0.0", port=self._port)
    # Start the server
    async def start():
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=proxy_port,
        )
        server = uvicorn.Server(config)
        await server.serve()

    # Run the asyncio event loop instead of uvloop to enable re entrance
    # import asyncio
    # asyncio.run(start())
    import asyncio
    loop = asyncio.new_event_loop()

    # Define a function to run the 'start' coroutine in the background thread
    import threading
    def start_in_thread():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start())

    # Create a thread and run the function in that thread
    thread = threading.Thread(target=start_in_thread, daemon=True)
    thread.start()
