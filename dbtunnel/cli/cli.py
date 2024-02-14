import os
import subprocess
from pathlib import Path

import click
from click import ClickException

from dbtunnel.frpc import DBTunnelConfig, ProxyWithNameAlreadyExists


@click.group()
def cli():
    """
    DBTunnel CLI to poke a hole to internet. This CLI is only for internal use.
    """

    pass


def validate_app_name(ctx, param, value):
    if value is None:
        return value
    if not value.isalnum():
        raise click.BadParameter('App name should only contain alphanumeric characters and no spaces.')
    return value

def is_frpc_installed(frpc_path: Path, silent=False):
    try:
        subprocess.run([str(frpc_path), "--help"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
        if silent is False:
            click.echo("✅  frpc is already installed.")
        return True
    except FileNotFoundError:
        click.echo("❌  frpc is not installed.")
        return False
    except subprocess.CalledProcessError:
        click.echo("❌  frpc is not installed.")
        return False


def brew_install_frpc():
    try:
        click.confirm('Do you want to install frpc via brew. dbtunnel will run: brew install frpc?', abort=True)
        env_copy = os.environ.copy()
        # do not update homebrew
        env_copy["HOMEBREW_NO_AUTO_UPDATE"] = "1"
        result = subprocess.run(["brew", "install", "frpc"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env_copy)
        output = result.stdout.decode("utf-8")
        click.echo(output)
        click.echo("✅  frpc finished installing.")
    except subprocess.CalledProcessError:
        raise ValueError("Error: Failed to install frpc using brew.")


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
        raise ValueError("❌  Homebrew is not installed. Please install homebrew (https://brew.sh/) and try again.")

def is_mac():
    import platform
    return platform.system() == 'Darwin'

def verify_installation(frpc_exec_path: Path):
    if is_mac() is False:
        raise ClickException("Error: Unsupported platform. Only MacOS is supported.")
    if is_frpc_installed(frpc_exec_path) is False:
        brew_install_frpc()
        # just double verify
        is_frpc_installed(frpc_exec_path, silent=True)
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


@cli.command()
@click.option('--tunnel-host', '-th', type=str, required=True, help='The domain of the dbtunnel server')
@click.option('--tunnel-port', '-tp', type=int, show_default=True,
              default=7000,
              help='The port of the dbtunnel server.')
@click.option('--local-host', '-h', type=str, default="0.0.0.0", help='The local host to bind')
@click.option('--local-port', '-p', type=int, required=True, help='The local port to bind')
@click.option('--app-name', '-n', type=str, required=True, callback=validate_app_name,
              help='The name of the app. Should be unique no spaces.')
@click.option('--subdomain', '-sd', type=str, callback=validate_app_name,
              help='The subdomain of the app. Should be unique no spaces.')
@click.option("--ssh", is_flag=True, show_default=True, default=False, help="Use ssh instead of native cli for tunnel.")
def bind(**kwargs):
    """
    Bind a local port to a dbtunnel server domain.
    """
    use_ssh_mode = kwargs.get('ssh')
    app_name = kwargs.get('app_name')
    tunnel_host = kwargs.get('tunnel_host').replace("https://", "").replace("https://", "").replace("/", "")
    tunnel_port = kwargs.get('tunnel_port')
    local_port = kwargs.get('local_port')
    local_host = kwargs.get('local_host')
    frpc_native_executable_path = None

    if use_ssh_mode is False:
        # usually you have ssh client installed on mac
        click.echo('Checking if binaries is installed')
        verify_homebrew()
        frpc_native_executable_path = get_frpc_homebrew_path()
        verify_installation(frpc_native_executable_path)
        click.echo('✅  Binaries Properly Installed')

    click.echo('✅  Using SSH Tunnel')
    click.echo(f'✅  Pushing {app_name} to dbtunnel server')
    click.echo(f'✅  Creating configuration file')

    db_tunnel_config = DBTunnelConfig(
        app_name=app_name,
        tunnel_host=tunnel_host,
        tunnel_port=tunnel_port,
        local_port=local_port,
        subdomain=app_name,
        executable_path=str(frpc_native_executable_path),
        mode='ssh' if use_ssh_mode else 'native',
    )
    db_tunnel_config.publish()
    try:
        click.echo(f'\n\t\t⚠️  Binding {local_host}:{local_port} to https://{app_name}.{tunnel_host}\n')
        db_tunnel_config.run()
    except ProxyWithNameAlreadyExists as e:
        raise click.ClickException(str(e))

