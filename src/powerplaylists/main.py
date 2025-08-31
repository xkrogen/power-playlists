#!/usr/bin/env python3

import logging
import os
import pathlib
import subprocess
import sys
import time
from logging import handlers
from typing import List, cast

import click
import lockfile
import psutil as psutil
import spotipy
from daemon import DaemonContext, pidfile
from lockfile import pidlockfile
from spotipy.oauth2 import SpotifyPKCE

from powerplaylists.spotify_client import SpotifyClient
from . import nodes, utils
from .nodes import OutputNode
from .utils import AppConfig, Constants, UserConfig, VerifyMode


def eprint(*values):
    print(*values, file=sys.stderr)


def exit_message(*message_print_values, exit_code=1):
    eprint(*message_print_values)
    exit(exit_code)


@click.group(context_settings=dict(max_content_width=9999))
@click.option(
    "--appconf",
    default=None,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to an app configuration YAML file. Defaults to " + Constants.APP_CONFIG_FILE_DEFAULT,
)
def cli(appconf: str):
    app_conf = AppConfig(appconf)
    utils.global_conf = app_conf


@cli.command()
@click.option(
    "--userconf",
    default=None,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    multiple=True,
    help="Path to a user configuration YAML file. Can be specified multiple times. "
    "If not specified, all files in the 'user_config_dir' config are used. "
    f"This defaults to {Constants.USER_CONFIG_DIR_DEFAULT}",
)
@click.option(
    "--verifymode",
    default="DEFAULT",
    type=click.Choice([vm.name for vm in VerifyMode] + ["DEFAULT"], case_sensitive=False),
    help="Whether to perform verification on updated playlists to ensure they matches expectation. "
    "DEFAULT will use the default value from the configuration file, "
    f"which is {Constants.VERIFY_MODE_DEFAULT.name} unless configured. "
    "END will verify playlist updates after all modifications are made. "
    "INCREMENTAL will verify playlist updates after each individual updates. "
    "This can be useful for debugging. NONE will never perform verification.",
)
@click.option(
    "--force/--no-force", default=False, help="Supply --force to ignore any caching and force-update all playlists."
)
def run(userconf: List[str], verifymode: str, force: bool):
    """Run a single iteration of the playlist updates."""
    app_conf = utils.global_conf
    if app_conf is None:
        raise RuntimeError("global_conf is not initialized")
    if verifymode != "DEFAULT":
        app_conf.verify_mode = VerifyMode[verifymode]
    app_conf.cache_force = force
    init_logging(app_conf)
    user_conf_files = app_conf.get_user_config_files(userconf)
    click.echo(f"Performing update based on user conf file(s): {', '.join(user_conf_files)}")
    try:
        perform_update_iteration(app_conf, user_conf_files)
    except BaseException as e:
        logging.error("Fatal exception encountered while performing update. Exiting.", exc_info=e)
        click.echo(f"Error encountered while performing an update: {e}", err=True)
        click.echo(f"Please see the log file for more details: {app_conf.log_file_path}", err=True)
        sys.exit(1)


@cli.group(
    help="Control the background process to keep playlists updated."
    + (
        " NOTE: On MacOS systems, the `launchd` commands provide a preferable alternative "
        "to the self-managed daemon provided by the `daemon` commands."
        if utils.is_macos()
        else ""
    )
)
def daemon():
    pass


@daemon.command()
def start():
    """Start a background process. If an existing process is found, an error will be thrown."""
    _start()


def _start():
    curr_pid = pidlockfile.read_pid_from_pidfile(utils.global_conf.daemon_pidfile)
    if curr_pid is not None:
        click.echo(
            f"Found existing daemon at PID {curr_pid}. Only one daemon is allowed to run concurrently. "
            f'Please kill the previous one using "power-playlists daemon stop".',
            err=True,
        )
        sys.exit(1)
    click.echo(f"Starting daemon with logging to {utils.global_conf.log_file_path}")
    context = DaemonContext(stdout=sys.stdout, stderr=sys.stderr)
    with context:
        daemon_run_loop(utils.global_conf)


@daemon.command()
def stop():
    """Stop an existing background process, if one exists."""
    _stop()


def _stop():
    curr_pid = pidlockfile.read_pid_from_pidfile(utils.global_conf.daemon_pidfile)
    if curr_pid is None:
        click.echo(f"No running daemon could be found! Checked for PID file at: {utils.global_conf.daemon_pidfile}")
    elif not psutil.pid_exists(curr_pid):
        click.echo(f"Found PID file with PID {curr_pid} but the process doesn't exist. Deleting stale PID file.")
        pidlockfile.remove_existing_pidfile(utils.global_conf.daemon_pidfile)
    else:
        running = psutil.Process(pid=curr_pid)
        click.echo(f"Killing daemon process at PID {curr_pid}...")
        running.kill()
        running.wait()
        # Remove the PID file just in case
        pidlockfile.remove_existing_pidfile(utils.global_conf.daemon_pidfile)
        click.echo("Successfully killed daemon process.")


@daemon.command()
def show():
    """Show information on whether there is currently a running daemon."""
    curr_pid = pidlockfile.read_pid_from_pidfile(utils.global_conf.daemon_pidfile)
    if curr_pid is None:
        click.echo(f"No daemon currently running. Checked for PID file at: {utils.global_conf.daemon_pidfile}")
    elif not psutil.pid_exists(curr_pid):
        click.echo(f"No daemon is running, but found stale PID file with PID {curr_pid}. Deleting stale file.")
        pidlockfile.remove_existing_pidfile(utils.global_conf.daemon_pidfile)
    else:
        click.echo(f"Daemon currently running at PID {curr_pid}")


@daemon.command()
def restart():
    """Stop an existing background process, if one exists, and start a new one."""
    _stop()
    _start()


@cli.group(hidden=not utils.is_macos())
def launchd():
    """
    Control integration with MacOS's `launchd` used for running power-playlists in the background.
    This is preferred over the `daemon` commands when running on a MacOS system.
    """
    pass


@launchd.command("install")
def launchd_install():
    """Install the daemon to be run in the background via `launchd`. Re-install to update configs."""
    assert utils.is_macos(), "launchd can only be used on MacOS platform"
    _launchd_uninstall()  # clear out any old service and plist files
    entrypoint = os.path.abspath(sys.modules["__main__"].__file__)
    appconf = utils.global_conf.app_config_path
    appconf_str = "" if appconf is None else f"<string>--appconf</string><string>{appconf}</string>"
    file_contents = Constants.MACOS_LAUNCHD_PLIST_FORMAT.format(
        scriptid=Constants.PACKAGE_HIERARCHICAL_NAME,
        entrypoint=entrypoint,
        stderr=f"{utils.global_conf.log_file_path}.err",
        stdout=f"{utils.global_conf.log_file_path}.out",
        run_interval=utils.global_conf.daemon_sleep_period_minutes * 60,
        appconf_param_str=appconf_str,
    )
    click.echo(f'Installing plist file at "{Constants.MACOS_LAUNCHD_PLIST_FILE}" ...')
    plist_path = os.path.expanduser(Constants.MACOS_LAUNCHD_PLIST_FILE)
    with open(plist_path, mode="w") as f:
        f.write(file_contents)
    click.echo(
        f"Successfully installed plist file to run every {utils.global_conf.daemon_sleep_period_minutes} minutes"
    )
    subprocess.run(["launchctl", "load", plist_path], check=True)
    if not _launchd_service_exists():
        raise ValueError("launchctl load appears to have been unsuccessful")
    click.echo("Loaded plist into launchd")
    click.echo(f"Logs will be sent to: {utils.global_conf.log_file_path}")


@launchd.command("uninstall")
def uninstall():
    """Uninstall the daemon from running via `launchd`."""
    assert utils.is_macos(), "launchd can only be used on MacOS platform"
    _launchd_uninstall()


def _launchd_service_exists():
    launchctl_print_cmd = ["launchctl", "print", f"gui/{os.getuid()}/{Constants.PACKAGE_HIERARCHICAL_NAME}"]
    launchctl_print = subprocess.run(launchctl_print_cmd, capture_output=True)
    return launchctl_print.returncode == 0


def _launchd_uninstall():
    plist_path = os.path.expanduser(Constants.MACOS_LAUNCHD_PLIST_FILE)
    if _launchd_service_exists():
        subprocess.run(["launchctl", "unload", plist_path], check=True)
        click.echo("Unloaded existing service from launchd")
    if os.path.exists(plist_path):
        os.remove(plist_path)
        click.echo(f"Deleted launchd plist file at {Constants.MACOS_LAUNCHD_PLIST_FILE}")


def init_logging(app_conf: AppConfig):
    root_logger = logging.getLogger()
    root_logger.setLevel(app_conf.log_file_level)
    file_handler = handlers.RotatingFileHandler(app_conf.log_file_path, maxBytes=1024 * 1024, backupCount=5)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-5.5s] [%(name)s] %(message)s"))
    file_handler.setLevel(logging.getLevelName(app_conf.log_file_level))
    root_logger.addHandler(file_handler)


def daemon_run_loop(app_conf: AppConfig):
    pid_file = pidfile.TimeoutPIDLockFile(app_conf.daemon_pidfile, acquire_timeout=1)
    try:
        with pid_file:
            for handler in logging.getLogger().handlers:
                logging.getLogger().removeHandler(handler)
            init_logging(app_conf)
            msg = f"Started daemon at PID {os.getpid()}"
            click.echo(msg)
            logging.info(msg)
            msg = f"Performing update iteration immediately, then every {app_conf.daemon_sleep_period_minutes} minutes"
            click.echo(msg)
            logging.info(msg)
            next_iteration_time = time.time()
            while True:
                try:
                    # Set maximum sleep to 10 minutes to avoid imprecision of long sleep time
                    curr_time = time.time()
                    while curr_time < next_iteration_time:
                        time.sleep(min(next_iteration_time - curr_time, 10 * 60))
                        curr_time = time.time()
                    next_iteration_time = curr_time + app_conf.daemon_sleep_period_minutes * 60
                    logging.info("Beginning playlist update iteration")
                    perform_update_iteration(app_conf, app_conf.get_user_config_files())
                    logging.info(
                        f"Update iteration completed, sleeping for {app_conf.daemon_sleep_period_minutes} minutes..."
                    )
                except (ValueError, spotipy.SpotifyException):
                    logging.exception("Exception encountered while performing update. Continuing.")
                except BaseException:
                    logging.exception("Fatal exception encountered while performing update. Exiting.")
                    raise
    except (lockfile.LockTimeout, lockfile.AlreadyLocked):
        msg = "Daemon unable to acquire PID file lock; exiting."
        click.echo(msg, err=True)
        logging.warning(msg)
        sys.exit(1)


def perform_update_iteration(app_conf: AppConfig, user_conf_files: List[str]):
    for f in user_conf_files:
        logging.info(f"Processing user conf file: {f}")
        user_conf = UserConfig(f)
        fname = os.path.basename(f)

        token_dir = f"{app_conf.cache_dir}/tokens"
        pathlib.Path(token_dir).mkdir(parents=True, exist_ok=True)
        pkce = SpotifyPKCE(
            client_id=app_conf.client_id,
            redirect_uri=app_conf.client_redirect_uri,
            cache_path=f"{token_dir}/{fname}.token",
            scope=Constants.SECURITY_SCOPES,
        )
        spotipy_client = spotipy.Spotify(auth_manager=pkce)
        spotify_client = SpotifyClient(app_conf, spotipy_client)

        try:
            try:
                node_list = nodes.resolve_node_list(spotify_client, user_conf.node_dicts.items())
            except ValueError as err:
                raise ValueError(f"Unable to parse definition of nodes for {fname}: {err}")
            output_nodes = [cast(OutputNode, node) for node in node_list if isinstance(node, OutputNode)]
            if len(output_nodes) == 0:
                raise ValueError(f"Unable to find any output nodes for {fname}")
            try:
                for out_node in output_nodes:
                    out_node.create_or_update()
            except ValueError as err:
                raise ValueError(f"Invalid definition for {fname}: {err}")
        finally:
            logging.info(f"Performed API calls for {fname}: {dict(spotify_client.api_call_counts)}")
            spotify_client.reset_api_call_counts()


if __name__ == "__main__":
    run()
