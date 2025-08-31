from __future__ import annotations

import html
import logging
import os
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime

import yaml
from dateutil import parser, tz
from spotipy import Spotify

from . import utils
from .utils import AppConfig, Constants

logger = logging.getLogger(__name__)


class SpotifyClient:
    def __init__(self, app_conf: AppConfig, spotipy_client: Spotify, enable_cache=True):
        self.spotipy = spotipy_client
        self.playlist_cache = PlaylistCache(app_conf, self.__load_playlist) if enable_cache else None
        self.force_reload: bool = app_conf.cache_force
        self.current_user_playlist_cache: dict[str, PlaylistDescription] = dict()
        self.current_user_playlists_loaded = False
        self.api_call_counts: defaultdict[str, int] = defaultdict(lambda: 0)

    def current_user(self) -> User:
        return User(self.spotipy.current_user())

    def reset_api_call_counts(self):
        self.api_call_counts.clear()

    def _increment_call_count(self, api_name):
        self.api_call_counts[api_name] = self.api_call_counts[api_name] + 1

    def current_user_playlists(self, force_reload: bool = False) -> list[PlaylistDescription]:
        if force_reload or not self.current_user_playlists_loaded:
            self._increment_call_count("current_user_playlists")
            user_playlists_resp = self.spotipy.current_user_playlists()
            playlist_list = user_playlists_resp["items"]
            while len(playlist_list) < int(user_playlists_resp["total"]):
                self._increment_call_count("current_user_playlists")
                user_playlists_resp = self.spotipy.current_user_playlists(
                    offset=len(playlist_list), limit=Constants.PAGINATION_LIMIT
                )
                playlist_list.extend(user_playlists_resp["items"])
            self.current_user_playlist_cache = {
                playlist["uri"]: PlaylistDescription(playlist) for playlist in playlist_list
            }
            self.current_user_playlists_loaded = True
        return [playlist for uri, playlist in self.current_user_playlist_cache.items()]

    def playlist(self, playlist_uri: str, force_reload: bool = False) -> Playlist:
        if not self.playlist_cache:
            return self.__load_playlist(playlist_uri)
        playlist, was_cached = self.playlist_cache.get_playlist(playlist_uri, force_reload or self.force_reload)
        if not was_cached:
            return playlist
        playlist_desc = self.playlist_description(playlist_uri)
        if playlist.snapshot_id != playlist_desc.snapshot_id:
            playlist, was_cached = self.playlist_cache.get_playlist(playlist_uri, force_reload=True)
        return playlist

    def playlist_description(self, playlist_uri: str, force_reload: bool = False) -> PlaylistDescription:
        if force_reload or self.force_reload or playlist_uri not in self.current_user_playlist_cache:
            self._increment_call_count("playlist")
            playlist_desc = PlaylistDescription(self.spotipy.playlist(playlist_uri))
            self.current_user_playlist_cache[playlist_uri] = playlist_desc
            return playlist_desc
        return self.current_user_playlist_cache[playlist_uri]

    def __load_playlist(self, playlist_uri) -> Playlist:
        self._increment_call_count("playlist")
        logging.debug(f"Loading playlist {playlist_uri} ...")
        playlist_resp = self.spotipy.playlist(playlist_uri)
        tracklist = playlist_resp["tracks"]["items"]
        total_tracks = int(playlist_resp["tracks"]["total"])
        while len(tracklist) < total_tracks:
            self._increment_call_count("playlist_items")
            additional_resp = self.spotipy.playlist_items(
                playlist_uri, offset=len(tracklist), limit=Constants.PAGINATION_LIMIT
            )
            tracklist.extend(additional_resp["items"])
        return Playlist(
            playlist_resp,
            [
                PlaylistTrack(track)
                for track in tracklist
                if track["track"] is not None
                and track["track"].get("type") == "track"
                and not utils.to_bool(track["is_local"])
            ],
        )

    def saved_tracks(self) -> list[SavedTrack]:
        self._increment_call_count("saved_tracks")
        resp = self.spotipy.current_user_saved_tracks()
        tracklist = resp["items"]
        total_tracks = int(resp["total"])
        while len(tracklist) < total_tracks:
            self._increment_call_count("saved_tracks")
            additional_resp = self.spotipy.current_user_saved_tracks(
                offset=len(tracklist), limit=Constants.PAGINATION_LIMIT
            )
            tracklist.extend(additional_resp["items"])
        return [SavedTrack(track) for track in tracklist]

    def create_playlist(
        self, playlist_name: str, description: str, public: bool = False, collaborative: bool = False
    ) -> Playlist:
        self._increment_call_count("user_playlist_create")
        new_playlist = Playlist(
            self.spotipy.user_playlist_create(
                self.current_user().oid, playlist_name, public, collaborative, description
            ),
            list(),
        )
        self.current_user_playlist_cache[new_playlist.uri] = new_playlist
        if self.playlist_cache:
            self.playlist_cache.set_cache_value(new_playlist.uri, new_playlist)
        return new_playlist

    def playlist_remove_specific_occurrences_of_items(
        self, playlist_uri: str, removal_tuple_list: list[tuple[str, int]], snapshot_id: str | None = None
    ) -> str:
        tracks_removed = 0
        # For pagination of removals, start at the end and work backwards to avoid changing the indices
        # of songs specified in subsequent calls
        if len(removal_tuple_list) == 0:
            return self.get_snapshot_id(
                "remove_specific_occurrences",
                self.spotipy.playlist_remove_specific_occurrences_of_items(playlist_uri, [], snapshot_id=snapshot_id),
            )

        while tracks_removed < len(removal_tuple_list):
            start_idx = -1 * (Constants.PAGINATION_LIMIT + tracks_removed)
            end_idx = None if tracks_removed == 0 else -tracks_removed
            tracks_to_remove = [{"uri": uri, "positions": [idx]} for uri, idx in removal_tuple_list[start_idx:end_idx]]
            self._increment_call_count("remove_specific_occurrences")
            snapshot_id = self.get_snapshot_id(
                "remove_specific_occurrences",
                self.spotipy.playlist_remove_specific_occurrences_of_items(
                    playlist_uri, tracks_to_remove, snapshot_id=snapshot_id
                ),
            )
            tracks_removed += len(tracks_to_remove)

        assert snapshot_id is not None  # Should be assigned in the loop above
        return snapshot_id

    def playlist_reorder_items(
        self,
        playlist_uri: str,
        range_start: int,
        insert_before: int,
        range_length: int = 1,
        snapshot_id: str | None = None,
    ) -> str:
        self._increment_call_count("playlist_reorder_items")
        response_dict = self.spotipy.playlist_reorder_items(
            playlist_uri, range_start, insert_before, range_length, snapshot_id=snapshot_id
        )
        return self.get_snapshot_id("playlist_reorder_items", response_dict)

    def get_snapshot_id(
        self, api_name: str, response: str | dict, original_resp: dict | None = None, depth: int = 0
    ) -> str:
        # Sometimes snapshot_id ends up being a dict. It's not clear why, but it is necessary to then
        # go one level deeper to extract the real snapshot_id.
        if isinstance(response, dict):
            snapshot_id = response["snapshot_id"]
            depth += 1
            if depth > 2:
                logger.info(
                    f"Found unexpected response from {api_name}. Attempting to find snapshot_id "
                    f"nested {depth}-deep within the response: {response}\n"
                    f"Full response:\n{original_resp}"
                )
            snapshot_id = self.get_snapshot_id(
                f"{api_name}['snapshot_id']",
                snapshot_id,
                original_resp=response if original_resp is None else original_resp,
                depth=depth,
            )
        else:
            snapshot_id = response
        return snapshot_id

    def playlist_add_items(self, playlist_uri: str, item_uris: list[str], snapshot_id: str | None = None) -> str:
        if len(item_uris) == 0:
            # If no items to add, return current snapshot_id or fetch it
            if snapshot_id is not None:
                return snapshot_id
            # Need to get current snapshot_id from playlist
            playlist = self.spotipy.playlist(playlist_uri)
            return playlist["snapshot_id"]

        tracks_added = 0
        while tracks_added < len(item_uris):
            tracks_to_add = item_uris[tracks_added : tracks_added + Constants.PAGINATION_LIMIT]
            self._increment_call_count("playlist_add_items")
            snapshot_id = self.get_snapshot_id(
                "playlist_add_items", self.spotipy.playlist_add_items(playlist_uri, tracks_to_add)
            )
            tracks_added += len(tracks_to_add)

        assert snapshot_id is not None  # Should be assigned in the loop above
        return snapshot_id

    def playlist_change_details(
        self,
        playlist_uri: str,
        name: str | None = None,
        public: bool | None = None,
        collaborative: bool | None = None,
        description: str | None = None,
    ):
        if ":" in playlist_uri:
            # playlist_change_details only accepts an ID, not a URI
            playlist_uri = playlist_uri.split(":")[2]
        self._increment_call_count("playlist_change_details")
        self.spotipy.playlist_change_details(playlist_uri, name, public, collaborative, description)

    def saved_tracks_contains(self, track_uris: list[str]) -> list[bool]:
        start_idx = 0
        track_matches: list[bool] = list()
        while start_idx < len(track_uris):
            next_track_uris = track_uris[start_idx : start_idx + Constants.PAGINATION_LIMIT]
            self._increment_call_count("current_user_saved_tracks_contains")
            track_matches.extend(self.spotipy.current_user_saved_tracks_contains(next_track_uris))
            start_idx += Constants.PAGINATION_LIMIT
        return track_matches


class PlaylistCache:
    PLAYLIST_CACHE_DIR_NAME = "playlists"

    def __init__(self, config: AppConfig, playlist_load_fn: Callable[[str], Playlist]):
        self.playlist_cache_dir = f"{config.cache_dir}/{PlaylistCache.PLAYLIST_CACHE_DIR_NAME}"
        self.playlist_load_fn = playlist_load_fn
        if not os.path.exists(self.playlist_cache_dir):
            os.makedirs(self.playlist_cache_dir, exist_ok=True)

    def get_playlist(self, playlist_uri: str, force_reload: bool = False) -> tuple[Playlist, bool]:
        playlist_path = self.__get_playlist_file(playlist_uri)
        if not force_reload and os.path.exists(playlist_path):
            with open(playlist_path) as f:
                return yaml.load(f, Loader=yaml.Loader), True
        playlist_obj = self.playlist_load_fn(playlist_uri)
        self.set_cache_value(playlist_uri, playlist_obj)
        return playlist_obj, False

    def set_cache_value(self, playlist_uri: str, playlist_obj: Playlist):
        playlist_path = self.__get_playlist_file(playlist_uri)
        if os.path.exists(playlist_path):
            os.remove(playlist_path)
        with open(playlist_path, mode="x") as f:
            yaml.dump(playlist_obj, stream=f)

    def __get_playlist_file(self, playlist_uri: str):
        return f"{self.playlist_cache_dir}/{playlist_uri.replace('spotify:playlist:', '')}"


class SpotifyWebObject:
    def __init__(self, obj_dict: dict):
        self._obj_dict = obj_dict
        self.uri: str = self._get_required_prop("uri")
        self.oid: str = self._get_required_prop("id")

    def _get_required_prop(self, key: str):
        if key not in self._obj_dict:
            raise ValueError(
                f"Malformed <{type(self).__name__}> received; missing key <{key}>. "
                f"Full object dict: {str(self._obj_dict)}"
            )
        return self._obj_dict[key]

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["_obj_dict"]
        return state

    def __eq__(self, other):
        if type(other) is type(self):
            return {k: v for k, v in self.__dict__.items() if k != "_obj_dict"} == {
                k: v for k, v in other.__dict__.items() if k != "_obj_dict"
            }
        else:
            return NotImplemented


# https://developer.spotify.com/documentation/web-api/reference/object-model/#user-object-public
class User(SpotifyWebObject):
    def __init__(self, obj_dict: dict):
        super().__init__(obj_dict)
        self.display_name: str = self._get_required_prop("display_name")


# https://developer.spotify.com/documentation/web-api/reference/object-model/#artist-object-simplified
class Artist(SpotifyWebObject):
    def __init__(self, obj_dict: dict):
        super().__init__(obj_dict)
        self.name: str = self._get_required_prop("name")


# https://developer.spotify.com/documentation/web-api/reference/object-model/#album-object-simplified
class Album(SpotifyWebObject):
    def __init__(self, obj_dict: dict):
        super().__init__(obj_dict)
        self.album_type: str = self._get_required_prop("album_type")  # 'album', 'single', 'compilation'
        self.artists: list[Artist] = [Artist(artist) for artist in self._get_required_prop("artists")]
        self.name: str = self._get_required_prop("name")
        # release_date is YYYY, YYYY-MM, or YYYY-MM-DD
        try:
            self.release_date = parser.isoparse(self._get_required_prop("release_date"))
        except ValueError:
            logging.warning(
                f"Failed to parse release date for album {self.name}: {self._get_required_prop('release_date')}"
            )
            self.release_date = datetime.min


# https://developer.spotify.com/documentation/web-api/reference/object-model/#track-object-simplified
class TrackSimplified(SpotifyWebObject):
    def __init__(self, obj_dict: dict):
        super().__init__(obj_dict)
        self.name: str = self._get_required_prop("name")
        self.artists: list[Artist] = [Artist(artist) for artist in self._get_required_prop("artists")]


# https://developer.spotify.com/documentation/web-api/reference/object-model/#track-object-full
class Track(TrackSimplified):
    def __init__(self, obj_dict: dict):
        super().__init__(obj_dict)
        self.popularity: int = self._get_required_prop("popularity")  # from 0 to 100
        self.album: Album = Album(self._get_required_prop("album"))


# https://developer.spotify.com/documentation/web-api/reference/object-model/#playlist-object-simplified
class PlaylistDescription(SpotifyWebObject):
    def __init__(self, obj_dict: dict):
        super().__init__(obj_dict)
        self.name: str = self._get_required_prop("name")
        self.collaborative: bool = self._get_required_prop("collaborative")
        self.description: str = self._get_required_prop("description")
        self.description = html.unescape(self.description) if self.description is not None else ""
        self.owner: User = User(self._get_required_prop("owner"))
        self.public: bool = self._get_required_prop("public")
        self.public = self.public if self.public is not None else False
        self.snapshot_id: str = self._get_required_prop("snapshot_id")


# https://developer.spotify.com/documentation/web-api/reference/object-model/#playlist-object-full
class Playlist(PlaylistDescription):
    def __init__(self, obj_dict: dict, all_tracks: list[PlaylistTrack]):
        super().__init__(obj_dict)
        self.follower_count: int = obj_dict["followers"]["total"]
        self.tracks: list[PlaylistTrack] = all_tracks


# https://developer.spotify.com/documentation/web-api/reference/object-model/#saved-track-object
class SavedTrack(Track):
    def __init__(self, obj_dict: dict):
        super().__init__(obj_dict["track"])
        self.added_at: datetime = parser.isoparse(obj_dict["added_at"]).astimezone(tz.tzutc()).replace(tzinfo=None)


# https://developer.spotify.com/documentation/web-api/reference/object-model/#playlist-track-object
class PlaylistTrack(SavedTrack):
    def __init__(self, obj_dict: dict):
        super().__init__(obj_dict)
        self.added_by: User = obj_dict["added_by"]
