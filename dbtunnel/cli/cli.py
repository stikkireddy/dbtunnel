import functools
import os
import subprocess
import webbrowser
from pathlib import Path

import click
from click import ClickException

from dbtunnel.relay import DBTunnelRelayClient, ProxyWithNameAlreadyExists, is_url_friendly, TunnelConfigError


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
        raise click.ClickException("❌  Please install frpc using brew. Run the following line: \n\nHOMEBREW_NO_AUTO_UPDATE=1 brew install frpc\n\n\n\n\n")
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
        raise click.ClickException("❌  Homebrew is not installed. Please install homebrew (https://brew.sh/) and try again.")

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
    webbrowser.open(url)

@cli.command()
@click.option("--headless", "-h", is_flag=True, show_default=True, default=False, help="Run without opening browser.")
@click.option("--debug", is_flag=True, show_default=True, default=False, help="Enable debug mode.")
@click.option('--tunnel-host', '-th', type=str, default="proxy.dbtunnel.app", help='The domain of the dbtunnel server')
@click.option('--tunnel-port', '-tp', type=int, show_default=True,
              default=7000,
              help='The port of the dbtunnel server.')
@click.option('--local-host', type=str, default="0.0.0.0", help='The local host to bind')
@click.option('--local-port', '-p', type=int, required=True, help='The local port to bind')
@click.option('--app-name', '-n', type=str, default=make_fake_name(), show_default=True, callback=validate_app_name,
              help='The name of the app. Should be unique no spaces.')
@click.option('--subdomain', '-sd', type=str, callback=validate_app_name,
              help='The subdomain of the app. Should be unique no spaces.')
@click.option("--private", is_flag=True, show_default=True, default=False,
              help="Causes the tunnel to be private and secured as setup by WAF rules.")
@click.option("--ssh", is_flag=True, show_default=True, default=False,
              help="Use ssh instead of native cli for tunnel.")
@click.option("--native", is_flag=True, show_default=True, default=False,
              help="Use native instead of ssh for tunnel.")
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
    local_port = kwargs.get('local_port')
    local_host = kwargs.get('local_host')
    is_private = kwargs.get('private')
    debug_mode = kwargs.get('debug')
    headless = kwargs.get('headless')
    frpc_native_executable_path = None

    def native_flow():
        click.echo('Checking if binaries is installed')
        verify_homebrew()
        exec_path = get_frpc_homebrew_path()
        verify_installation(exec_path)
        click.echo('✅  Binaries Properly Installed')
        return exec_path

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


    click.echo('✅  Using SSH Tunnel')
    click.echo(f'✅  Pushing {app_name} to dbtunnel server via: {"native" if use_ssh_mode is False else "ssh tunnel"}')
    try:
        db_tunnel_relay_client = DBTunnelRelayClient(
            app_name=app_name,
            tunnel_host=tunnel_host,
            tunnel_port=tunnel_port,
            local_port=local_port,
            subdomain=app_name,
            executable_path=str(frpc_native_executable_path),
            mode='ssh' if use_ssh_mode else 'native',
            private=is_private,
            log_level="debug" if debug_mode else "info"
        )

        click.clear()
        click.echo(click.style(f'DBTunnel by @stikkireddy\n', fg='green', bold=True))
        click.echo(f'💼 App Name: {click.style(app_name, fg="green")} | '
                   f'Type: {click.style("TCP over SSH Tunnel" if use_ssh_mode is True else "TCP Tunnel", fg="green")}\n')
        local_url = f'http://{local_host}:{local_port}'
        local_url = f"\033]8;;{local_url}\033\\{local_url}\033]8;;\033\\"
        styled_local_url = click.style(local_url, fg="cyan")
        click.echo(f'🚀 Local URL: {styled_local_url}\n')
        url = db_tunnel_relay_client.public_url()
        hyper_link = f'\033]8;;{url}\033\\{url}\033]8;;\033\\'
        click.echo(f'🔗 {"SSO Secured" if is_private else "Public Sharable"} URL: {click.style(hyper_link, fg="green")}\n',)

        click.echo(click.style('Tunnel Logs: ', fg='green', bold=True))
        open_browser_f = functools.partial(open_browser, url)
        db_tunnel_relay_client.run(output_func=click.echo,
                                   success_callback=open_browser_f if is_interactive() and headless is False else None)
    except ProxyWithNameAlreadyExists as e:
        raise click.ClickException(str(e))
    except TunnelConfigError as e:
        raise click.ClickException(f"Error Configuring Tunnel: {str(e)}")
    except subprocess.CalledProcessError as e:
        click.secho("\n\n❌  uhoh something happened.", fg="red", bold=True)
        styled_error = click.style(f"failed to create tunnel, please read the logs above to resolve the error",
                                   fg="red", bold=True)
        styled_error = click.style(f"if you get an error indicating that the proxy already exists please use -n to "
                                   f"provide a unique name", fg="red", bold=True)
        raise click.ClickException(styled_error)

