import functools
import os
import secrets
import socket
import subprocess
import webbrowser
from pathlib import Path

import click
from click import ClickException

from dbtunnel.relay import DBTunnelRelayClient, ProxyWithNameAlreadyExists, is_url_friendly, TunnelConfigError, \
    StandardProxyError


@click.group()
def cli():
    """
    DBTunnel CLI to poke a hole to internet. This CLI is only for internal use.
    """

    pass


def validate_app_name(ctx, param, value):
    if value is None:
        return value
    if is_url_friendly(value) is False:
        raise click.BadParameter('App name should only contain alphanumeric characters and no spaces.')
    return value


def is_frpc_installed(frpc_path: Path, silent=False):
    stdout_str = None
    stderr_str = None
    try:
        output = subprocess.run([str(frpc_path), "--help"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=os.environ)
        stdout_str = output.stdout.decode("utf-8").strip()
        stderr_str = output.stderr.decode("utf-8").strip()
        if silent is False:
            click.echo("✅  frpc is already installed.")
        return True
    except FileNotFoundError:
        click.clear()
        click.echo("❌  frpc is not installed.\n")
        raise click.ClickException(
            "❌  Please install frpc using brew. Run the following line: \n\nHOMEBREW_NO_AUTO_UPDATE=1 brew install frpc\n\n\n\n\n")
    except subprocess.CalledProcessError:
        click.echo("❌  uhoh something happened.")
        click.echo(f"stdout: {stdout_str}")
        click.echo(f"stderr: {stderr_str}")
        return False


def get_frpc_homebrew_path() -> Path:
    try:
        result = subprocess.run(["brew", "--prefix"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=os.environ)
        output = result.stdout.decode("utf-8").strip()
        return Path(output) / "bin" / "frpc"
    except subprocess.CalledProcessError:
        raise ValueError("Error: unable to find brew --prefix.")


def verify_homebrew():
    try:
        subprocess.run(["brew", "--help"], check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                       env=os.environ)
        click.echo("✅  Homebrew is installed.")
        return True
    except Exception:
        click.clear()
        click.echo("❌  Homebrew is not installed.\n")
        raise click.ClickException(
            "❌  Homebrew is not installed. Please install homebrew (https://brew.sh/) and try again.")


def is_mac():
    import platform
    return platform.system() == 'Darwin'


def verify_installation(frpc_exec_path: Path):
    if is_mac() is False:
        raise ClickException("Error: Unsupported platform. Only MacOS is supported for native connection.")
    if is_frpc_installed(frpc_exec_path) is False:
        # just double verify
        is_frpc_installed(frpc_exec_path)
        click.echo(f"✅  frpc is installed at path: {frpc_exec_path}.")


@cli.command()
def validate():
    """
    Validate if frpc is installed and working.
    """
    click.echo('Checking if binaries is installed')
    verify_homebrew()
    frpc_path = get_frpc_homebrew_path()
    verify_installation(frpc_path)
    click.echo('✅  Binaries Properly Installed')


def make_fake_name():
    login = os.getlogin()
    # replace . with - and remove all other special characters
    new_login = login.lower().replace(".", "-")
    return "".join([c for c in new_login if c.isalnum() or c == "-"])


def is_interactive():
    return os.isatty(0)


def open_browser(url):
    webbrowser.open_new_tab(url)


def make_visitor_command_string(app_name, secret_value):
    return f"dbtunnel visit -n {app_name} -s {secret_value}"


def native_flow():
    click.echo('Checking if binaries is installed')
    verify_homebrew()
    exec_path = get_frpc_homebrew_path()
    verify_installation(exec_path)
    click.echo('✅  Binaries Properly Installed')
    return exec_path


def find_next_open_port(*, host="0.0.0.0", start_port: int = 9000, end_port: int = 9999):
    for port in range(start_port, end_port + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # Set a timeout for the connection attempt
        result = sock.connect_ex((host, port))
        if result != 0:  # 0 means the port is open
            return port
        sock.close()

    return None


@cli.command()
@click.option("--headless", "-h", is_flag=True, show_default=True, default=False, help="Run without opening browser.")
@click.option('--tunnel-host', '-th', type=str, required=True,
              help='The domain of the dbtunnel server')
@click.option('--tunnel-port', '-tp', type=int, show_default=True,
              default=7000,
              help='The port of the dbtunnel server.')
@click.option('--local-host', type=str, default="0.0.0.0", help='The local host to bind')
@click.option('--local-port', '-p', type=int, default=find_next_open_port(), help='The local port to bind')
@click.option('--app-name', '-n', type=str, default=make_fake_name(), show_default=True, callback=validate_app_name,
              help='The name of the app. Should be unique no spaces.')
@click.option("--secret-value", "-s", show_default=True, default=lambda: secrets.token_urlsafe(32),
              help="Visitor secret value.")
def visit(**kwargs):
    app_name = kwargs.get('app_name')
    tunnel_host = kwargs.get('tunnel_host').replace("https://", "").replace("https://", "").replace("/", "")
    tunnel_port = kwargs.get('tunnel_port')
    local_port = kwargs.get('local_port')
    local_host = kwargs.get('local_host')
    debug_mode = kwargs.get('debug')
    headless = kwargs.get('headless')
    secret_value = kwargs.get('secret_value')

    frpc_native_executable_path = native_flow()

    try:
        db_tunnel_relay_client = DBTunnelRelayClient(
            app_name=app_name,
            tunnel_host=tunnel_host,
            tunnel_port=tunnel_port,
            local_port=local_port,
            local_host=local_host,
            subdomain=app_name,
            executable_path=str(frpc_native_executable_path),
            mode='native',
            log_level="debug" if debug_mode else "info",
            secret=True,
            secret_string=secret_value,
            visitor=True
        )
        click.clear()
        click.echo(click.style(f'DBTunnel by @stikkireddy\n', fg='green', bold=True))
        click.echo(f'💼 Welcome to: {click.style(app_name, fg="green")} | '
                   f'Type: Visiting App via TCP Tunnel \n')
        local_url = f'http://{local_host}:{local_port}'
        styled_local_url = f"\033]8;;{local_url}\033\\{local_url}\033]8;;\033\\"
        styled_local_url = click.style(styled_local_url, fg="cyan")
        click.echo(f'🚀 Local URL: {styled_local_url}\n')

        open_browser_f = functools.partial(open_browser, local_url)
        click.echo(click.style('Tunnel Logs: ', fg='green', bold=True))
        db_tunnel_relay_client.run(output_func=click.echo,
                                   success_callback=open_browser_f if headless is False else None)
    except (ProxyWithNameAlreadyExists, StandardProxyError) as e:
        raise click.ClickException(str(e))
    except TunnelConfigError as e:
        raise click.ClickException(f"Error Configuring Tunnel: {str(e)}")
    except subprocess.CalledProcessError as e:
        click.secho("\n\n❌  uhoh something happened.", fg="red", bold=True)
        styled_error = click.style(f"if you get an error indicating that the proxy already exists please use -n to "
                                   f"provide a unique name", fg="red", bold=True)
        raise click.ClickException(styled_error)


@cli.command()
@click.option("--headless", "-h", is_flag=True, show_default=True, default=False, help="Run without opening browser.")
@click.option("--debug", is_flag=True, show_default=True, default=False, help="Enable debug mode.")
@click.option('--tunnel-host', '-th', type=str, required=True, help='The domain of the dbtunnel server')
@click.option('--app-host', '-ah', type=str, required=True, help='The domain where the app is going to be served from')
@click.option('--tunnel-port', '-tp', type=int, show_default=True,
              default=7000,
              help='The port of the dbtunnel server.')
@click.option('--local-host', type=str, default="0.0.0.0", help='The local host to bind')
@click.option('--local-port', '-p', type=int, required=True, help='The local port to bind')
@click.option('--app-name', '-n', type=str, default=make_fake_name(), show_default=True, callback=validate_app_name,
              help='The name of the app. Should be unique no spaces.')
@click.option('--subdomain', '-sd', type=str, callback=validate_app_name,
              help='The subdomain of the app. Should be unique no spaces.')
@click.option("--sso", is_flag=True, show_default=True, default=False,
              help="Causes the tunnel to require sso via cloudflare zero trust and secured as setup by WAF rules.")
@click.option("--ssh", is_flag=True, show_default=True, default=False,
              help="Use ssh instead of native cli for tunnel.")
@click.option("--native", is_flag=True, show_default=True, default=False,
              help="Use native instead of ssh for tunnel.")
@click.option("--secret", is_flag=True, show_default=True, default=False,
              help="Entirely private connection, no public urls.")
@click.option("--secret-value", show_default=True, default=lambda: secrets.token_urlsafe(32),
              help="Private key for your visitors.")
def bind(**kwargs):
    """
    Bind a local port to a dbtunnel server domain.
    """
    use_ssh_mode = kwargs.get('ssh')
    use_native_mode = kwargs.get('native')
    use_best_mode = use_ssh_mode is False and use_native_mode is False
    app_name = kwargs.get('app_name')
    tunnel_host = kwargs.get('tunnel_host').replace("https://", "").replace("https://", "").replace("/", "")
    tunnel_port = kwargs.get('tunnel_port')
    app_host = kwargs.get('app_host').replace("https://", "").replace("https://", "").replace("/", "")
    local_port = kwargs.get('local_port')
    local_host = kwargs.get('local_host')
    sso = kwargs.get('sso')
    debug_mode = kwargs.get('debug')
    headless = kwargs.get('headless')
    secret = kwargs.get('secret')
    secret_value = kwargs.get('secret_value')
    frpc_native_executable_path = None

    if use_native_mode is True:
        # usually you have ssh client installed on mac
        frpc_native_executable_path = native_flow()

    if use_best_mode is True:
        try:
            frpc_native_executable_path = native_flow()
        except ClickException:
            click.echo("❌  Native mode failed. Trying ssh tunnel instead.")
            use_ssh_mode = True
            del use_native_mode

    click.echo(f'✅  Pushing {app_name} to dbtunnel server via: {"native" if use_ssh_mode is False else "ssh tunnel"}')
    try:
        db_tunnel_relay_client = DBTunnelRelayClient(
            app_name=app_name,
            tunnel_host=tunnel_host,
            tunnel_port=tunnel_port,
            local_port=local_port,
            app_host=app_host,
            subdomain=app_name,
            executable_path=str(frpc_native_executable_path),
            mode='ssh' if use_ssh_mode else 'native',
            sso=sso,
            log_level="debug" if debug_mode else "info",
            secret=secret,
            secret_string=secret_value
        )

        click.clear()
        click.echo(click.style(f'DBTunnel by @stikkireddy\n', fg='green', bold=True))
        click.echo(f'💼 App Name: {click.style(app_name, fg="green")} | '
                   f'Type: {click.style("TCP over SSH Tunnel" if use_ssh_mode is True else "TCP Tunnel", fg="green")}\n')
        local_url = f'http://{local_host}:{local_port}'
        local_url = f"\033]8;;{local_url}\033\\{local_url}\033]8;;\033\\"
        styled_local_url = click.style(local_url, fg="cyan")
        click.echo(f'🚀 APP URL: {styled_local_url}\n')

        open_browser_f = None

        # public url is only for non secret apps
        if secret is False:
            url = db_tunnel_relay_client.public_url()
            hyper_link = f'\033]8;;{url}\033\\{url}\033]8;;\033\\'
            click.echo(
                f'🔗 {"SSO Secured" if sso else "Public Sharable"} URL: {click.style(hyper_link, fg="green")}\n', )
            open_browser_f = functools.partial(open_browser, url)
        else:
            click.echo(f'🔒 Visitor Command: '
                       f'{click.style(make_visitor_command_string(app_name, secret_value), fg="green")}\n')
        click.echo(click.style('Tunnel Logs: ', fg='green', bold=True))
        db_tunnel_relay_client.run(output_func=click.echo,
                                   success_callback=open_browser_f if is_interactive() and headless is False else None)
    except (ProxyWithNameAlreadyExists, StandardProxyError) as e:
        raise click.ClickException(str(e))
    except TunnelConfigError as e:
        raise click.ClickException(f"Error Configuring Tunnel: {str(e)}")
    except subprocess.CalledProcessError as e:
        click.secho("\n\n❌  uhoh something happened.", fg="red", bold=True)
        styled_error = click.style(f"if you get an error indicating that the proxy already exists please use -n to "
                                   f"provide a unique name", fg="red", bold=True)
        raise click.ClickException(styled_error)
