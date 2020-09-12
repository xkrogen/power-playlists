#!/usr/bin/env python3

import yaml
import sys
import os

import spotipy
from spotipy.oauth2 import SpotifyPKCE

from constants import Constants

with open(Constants.get_app_config_file()) as app_conf_f:
    conf_yaml = yaml.safe_load(app_conf_f)
    client_id = conf_yaml['client_id']
    client_redirect_uri = conf_yaml['client_redirect_uri']
    if client_id is None or client_redirect_uri is None:
        print("Invalid app config file!", file=sys.stderr)
        exit(1)

for f in os.listdir(Constants.get_user_config_dir()):
    with open(f"{Constants.get_user_config_dir()}/{f}") as user_conf_f:
        conf_yaml = yaml.safe_load(user_conf_f)
        username = conf_yaml['username']
        if username is None:
            print("Invalid user conf_yaml file!", file=sys.stderr)
            exit(1)

    pkce = SpotifyPKCE(client_id=client_id,
                       redirect_uri=client_redirect_uri,
                       cache_path=f"cache/tokens/{username}.token",
                       scope=Constants.SECURITY_SCOPES,
                       username=username)
    sp = spotipy.Spotify(auth_manager=pkce)
 
    results = sp.current_user_saved_tracks()
    for idx, item in enumerate(results['items']):
        track = item['track']
        print(idx, track['artists'][0]['name'], " – ", track['name'])