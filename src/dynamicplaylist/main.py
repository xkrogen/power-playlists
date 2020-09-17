#!/usr/bin/env python3

import logging
import sys
from typing import List, cast

import click
import spotipy
from spotipy.oauth2 import SpotifyPKCE

from . import nodes, utils
from .nodes import OutputNode
from .utils import AppConfig, Constants, UserConfig


def eprint(*values):
    print(*values, file=sys.stderr)


def exit_message(*message_print_values, exit_code=1):
    eprint(*message_print_values)
    exit(exit_code)


@click.command()
@click.option('--appconf',
              default=None,
              type=click.Path(exists=True, dir_okay=False, resolve_path=True),
              help='Path to an app configuration YAML file.')
@click.option('--userconf',
              default=None,
              type=click.Path(exists=True, dir_okay=False, resolve_path=True),
              multiple=True,
              help='Path to a user configuration YAML file. Can be specified multiple times.')
@click.option('--loglevel',
              default='WARNING',
              show_default=True,
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Log level to use for console (stderr) logging.')
@click.option('--verify',
              default=None,
              is_flag=True,
              help='Whether to perform verification on the output playlist to ensure it matches expectation. '
                   'Recommended when executing a scenario for the first time, or after it has been modified.')
def cli(appconf: str, userconf: List[str], loglevel: str, verify: bool):
    app_conf = AppConfig(appconf)
    utils.global_conf = app_conf
    if verify is not None:
        app_conf.verify_mode = verify

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(app_conf.log_file_path, mode='a' if app_conf.log_file_append else 'w')
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-5.5s] [%(name)s] %(message)s"))
    file_handler.setLevel(logging.getLevelName(app_conf.log_file_level))
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] [%(name)s] %(message)s"))
    console_handler.setLevel(logging.getLevelName(loglevel))
    root_logger.addHandler(console_handler)

    for f in app_conf.get_user_config_files(userconf):
        user_conf = UserConfig(f)

        pkce = SpotifyPKCE(client_id=app_conf.client_id,
                           redirect_uri=app_conf.client_redirect_uri,
                           cache_path=f"{app_conf.cache_dir}/tokens/{user_conf.username}.token",
                           scope=Constants.SECURITY_SCOPES,
                           username=user_conf.username)
        spotipy_client = spotipy.Spotify(auth_manager=pkce)

        for scenario in user_conf.scenario_dicts:
            try:
                node_list = nodes.resolve_node_list(spotipy_client, scenario['nodes'].items())
            except ValueError as err:
                raise ValueError(f'Unable to parse definition of {scenario["name"]}: {err}')
            output_nodes = [cast(OutputNode, node) for node in node_list if node.ntype == 'output']
            if len(output_nodes) == 0:
                raise ValueError(f'Unable to find any output nodes for {scenario["name"]}')
            try:
                for out_node in output_nodes:
                    out_node.create_or_update()
            except ValueError as err:
                raise ValueError(f'Invalid definition for {scenario["name"]}: {err}')


if __name__ == '__main__':
    cli()
