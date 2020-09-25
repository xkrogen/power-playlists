from __future__ import annotations

import abc
import functools
import logging
import re
from abc import ABC
from typing import Dict, Iterable, List, Union, cast

import spotipy
from spotipy import Spotify

from . import utils
from .utils import Constants

NestedStrDict = Dict[str, Union[str, 'NestedStrDict', List['NestedStrDict']]]
logger = logging.getLogger(__name__)


def resolve_node_list(spotipy_client: Spotify,
                      unresolved_node_list: Iterable[(str, NestedStrDict)]) -> List[Node]:
    node_map_unresolved = {node_id: Node.from_dict(spotipy_client, node_id, node_dict)
                           for node_id, node_dict in unresolved_node_list}
    node_map = node_map_unresolved
    while len([n for n in node_map_unresolved.values() if n.ntype == 'template']) > 0:
        node_map = {}
        for node in node_map_unresolved.values():
            for res_nid, res_node in node.resolve_template().items():
                node_map[res_nid] = res_node
        node_map_unresolved = node_map
    for node in node_map.values():
        node.resolve_inputs(node_map)
    node_list = list(node_map.values())
    output_nodes = [cast(OutputNode, node) for node in node_list if node.ntype == 'output']
    input_nodes = [cast(InputNode, node) for node in node_list if node.ntype == 'input']
    input_playlist_names = {spotipy_client.playlist(node.get_required_prop('uri'))['name']
                            for node in input_nodes
                            if node.source_type() == 'playlist'}
    output_playlist_names = {node.playlist_name() for node in output_nodes}
    intersection = input_playlist_names.intersection(output_playlist_names)
    if len(intersection) != 0:
        raise ValueError(f'Found an invalid scenario definition; the following playlists are both input '
                         f'and output playlists: {intersection}')
    return node_list


class Node(ABC):
    def __init__(self, **kwargs):
        self.spotipy: Spotify = kwargs['spotipy_client']
        self.nid: str = kwargs['node_id']
        self.ntype: str = kwargs['type']
        self.__fulldict: Dict = kwargs

    @staticmethod
    def from_dict(spotipy_client: Spotify, node_id: str, node_dict: Dict):
        if 'type' not in node_dict:
            raise ValueError(f'Invalid definition for node <{node_id}>; unable to find "type" specifier')
        ntype = node_dict['type']
        if ntype == 'input':
            return InputNode(spotipy_client=spotipy_client, node_id=node_id, **node_dict)
        elif ntype == 'output':
            return OutputNode(spotipy_client=spotipy_client, node_id=node_id, **node_dict)
        elif ntype == 'template':
            return TemplateNode(spotipy_client=spotipy_client, node_id=node_id, **node_dict)
        else:
            return LogicNode(spotipy_client=spotipy_client, node_id=node_id, **node_dict)

    @abc.abstractmethod
    def tracks(self) -> List[NestedStrDict]:
        pass

    def resolve_inputs(self, node_dict: Dict[str, Node]) -> None:
        pass

    def resolve_template(self) -> Dict[str, 'Node']:
        return {self.nid: self}

    def has_prop(self, prop_key: str):
        return prop_key in self.__fulldict

    def get_required_prop(self, prop_key: str):
        if prop_key not in self.__fulldict:
            raise ValueError(f'Node <{self.nid}> requires prop <{prop_key}> but was not found')
        return self.__fulldict[prop_key]

    def get_optional_prop(self, prop_key: str, default_value):
        return self.__fulldict.get(prop_key, default_value)

    def _playlist_all_items(self, uri) -> NestedStrDict:
        playlist_resp = self.spotipy.playlist(uri)
        tracklist = playlist_resp['tracks']['items']
        total_tracks = int(playlist_resp['tracks']['total'])
        while len(tracklist) < total_tracks:
            additional_resp = self.spotipy.playlist_items(uri, offset=len(tracklist), limit=Constants.PAGINATION_LIMIT)
            tracklist.extend(additional_resp['items'])
        playlist_resp['tracks']['items'] = tracklist
        return playlist_resp


class InputNode(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.ntype != 'input':
            raise ValueError(f'Unexpected type <{self.ntype}> for node <{self.nid}>')
        self.track_cache = None

    def source_type(self) -> str:
        return self.get_required_prop('source_type')

    def tracks(self) -> List[NestedStrDict]:
        if self.source_type() == 'playlist':
            if self.track_cache is None:
                self.track_cache = self._playlist_all_items(self.get_required_prop('uri'))['tracks']['items']
            return self.track_cache
        else:
            raise ValueError(f"Unsupported source_type for 'input' node <{self.nid}>")


class NonleafNode(Node, ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.ntype == 'input':
            raise ValueError(f'Unexpected type <{self.ntype}> for node <{self.nid}>')
        self.input_nids: List[str] = kwargs['inputs']
        self.inputs: List[Node] = list()

    def resolve_inputs(self, node_dict: Dict[str, Node]):
        self.inputs = [node_dict[node_id] for node_id in self.input_nids]


class OutputNode(NonleafNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.ntype != 'output':
            raise ValueError(f'Unexpected type <{self.ntype}> for node <{self.nid}>')

    def input_node(self):
        if len(self.inputs) != 1:
            raise ValueError(f'Unexpected number of inputs for output node <{self.nid}>')
        if type(self.inputs[0]) != LogicNode or self.inputs[0].ntype != 'dedup':
            raise ValueError(f'Duplicates are not currently supported, so all output nodes must be preceded by '
                             f'a dedup node.')
        return self.inputs[0]

    def tracks(self):
        return self.input_node().tracks()

    def playlist_name(self) -> str:
        return self.get_required_prop('playlist_name')

    def create_or_update(self):
        user_playlists_resp = self.spotipy.current_user_playlists()
        playlist_list = user_playlists_resp['items']
        while len(playlist_list) < int(user_playlists_resp['total']):
            user_playlists_resp = self.spotipy.current_user_playlists(offset=len(playlist_list),
                                                                      limit=Constants.PAGINATION_LIMIT)
            playlist_list.extend(user_playlists_resp['items'])
        matching_playlist_uris = [pl['uri'] for pl in playlist_list if pl['name'] == self.playlist_name()]
        is_public = bool(self.get_optional_prop('public', False))
        description = self.get_optional_prop('description', 'Auto-generated dynamic playlist')
        if len(matching_playlist_uris) > 1:
            raise ValueError(f'Found {len(matching_playlist_uris)} with name "{self.playlist_name()}". '
                             f'Expected to find 1 or none. Refusing to update any of them.')
        elif len(matching_playlist_uris) == 1:
            playlist_uri = matching_playlist_uris[0]
            playlist = self._playlist_all_items(playlist_uri)
            if playlist['public'] != is_public or playlist['description'] != description:
                self.spotipy.playlist_change_details(playlist['id'], public=is_public, description=description)
            existing_track_uris = [track['track']['uri'] for track in playlist['tracks']['items']]
        else:
            user = self.spotipy.current_user()
            playlist = \
                self.spotipy.user_playlist_create(user['id'], self.playlist_name(), is_public, False, description)
            playlist_uri = playlist['uri']
            existing_track_uris = list()
        snapshot_id = playlist['snapshot_id']

        # create set of new/updated/removed/etc. tracks
        expected_output_track_uris = [track['track']['uri'] for track in self.tracks()]
        expected_output_track_uri_set = set(expected_output_track_uris)
        existing_track_uri_set = set(existing_track_uris)
        # Step 1: Remove tracks that shouldn't be there at all
        required_removals = [{'uri': uri, 'positions': [idx]}
                             for idx, uri in enumerate(existing_track_uris)
                             if uri not in expected_output_track_uri_set]
        # TODO some of this logic is going to have trouble with duplicates currently...
        if len(required_removals) > 0:
            tracks_removed = 0
            # For pagination of removals, start at the end and work backwards to avoid changing the indices
            # of songs specified in subsequent calls
            while tracks_removed < len(required_removals):
                start_idx = -1 * (Constants.PAGINATION_LIMIT + tracks_removed)
                end_idx = None if tracks_removed == 0 else -tracks_removed
                tracks_to_remove = required_removals[start_idx:end_idx]
                snapshot_id = self.spotipy. \
                    playlist_remove_specific_occurrences_of_items(playlist_uri, tracks_to_remove,
                                                                  snapshot_id=playlist['snapshot_id'])['snapshot_id']
                tracks_removed += len(tracks_to_remove)
            self.verify_playlist_contents([uri for uri in existing_track_uris if uri in expected_output_track_uri_set],
                                          playlist_uri, 'item removal')

        # Step 2: Add new tracks
        new_track_uris = [uri for uri in expected_output_track_uris if uri not in existing_track_uri_set]
        if len(new_track_uris) > 0:
            tracks_added = 0
            while tracks_added < len(new_track_uris):
                tracks_to_add = new_track_uris[tracks_added:tracks_added + Constants.PAGINATION_LIMIT]
                snapshot_id = self.spotipy.playlist_add_items(playlist_uri, tracks_to_add)
                tracks_added += len(tracks_to_add)
            expected_ordering = [uri for uri in existing_track_uris
                                 if uri in expected_output_track_uri_set] + new_track_uris
            self.verify_playlist_contents(expected_ordering, playlist_uri, 'item addition')

        # Step 3: Reorder tracks currently in the playlist to match the expected order
        current_track_uris = [uri for uri in existing_track_uris if uri in expected_output_track_uri_set] + \
            new_track_uris
        if set(current_track_uris) != expected_output_track_uri_set \
                or len(current_track_uris) != len(expected_output_track_uris):
            raise ValueError(f'TODO')
        elif current_track_uris != expected_output_track_uris:
            # TODO can't handle duplicates
            while current_track_uris != expected_output_track_uris:
                target_idx, target_uri = next((target_idx, uri)
                                              for target_idx, uri in enumerate(expected_output_track_uris)
                                              if current_track_uris[target_idx] != uri)
                start_idx = current_track_uris.index(target_uri)
                logger.info(f'Swapping pos {start_idx} into pos {target_idx} (uri <{target_uri}>)')
                # TODO attempt to group ranges to reduce API call volume
                try:
                    snapshot_id = self.spotipy.playlist_reorder_items(playlist_uri, start_idx, target_idx,
                                                                      snapshot_id=snapshot_id)['snapshot_id']
                    # Sometimes snapshot_id ends up being a dict. It's not clear why, but it is necessary to then
                    # go one level deeper to extract the real snapshot_id.
                    if type(snapshot_id) == Dict:
                        snapshot_id = snapshot_id['snapshot_id']
                except spotipy.SpotifyException as se:
                    logger.error(f'Encountered error while attempting to reorder items. playlist_uri={playlist_uri}, '
                                 f'start_idx={start_idx}, target_idx={target_idx}, snapshot_id={snapshot_id}',
                                 exc_info=se)
                    raise se
                current_track_uris.insert(target_idx, current_track_uris.pop(start_idx))
            self.verify_playlist_contents(expected_output_track_uris, playlist_uri, 'reordering')

    def verify_playlist_contents(self, expected_uris: List[str], playlist_uri: str, action_description: str):
        if utils.global_conf.verify_mode:
            playlist = self._playlist_all_items(playlist_uri)
            uris = [track['track']['uri'] for track in playlist['tracks']['items']]
            if uris != expected_uris:
                raise ValueError(f'Playlist {action_description} for <{self.nid}> resulted in unexpected contents.\n'
                                 f'Expected {len(expected_uris)} items and found {len(uris)}.\n'
                                 f'Found missing items: {set(expected_uris) - set(uris)}.\n'
                                 f'Found unexpected items: {set(uris) - set(expected_uris)}.\n'
                                 f'Expected items: {expected_uris}.\nFound items: {uris}.')


class LogicNode(NonleafNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assert_input_count(self, expected_count):
        if len(self.inputs) != expected_count:
            raise ValueError(f'Nodes of type {self.ntype} are expected to have {expected_count} inputs, but '
                             f'node <{self.nid}> had {len(self.inputs)}')

    def tracks(self):
        if self.ntype == 'combiner':
            return functools.reduce(lambda l1, l2: l1 + l2, map(lambda i: i.tracks(), self.inputs))
        elif self.ntype == 'sort':
            self.assert_input_count(1)
            sort_key = self.get_required_prop('sort_key')
            sort_desc = bool(self.get_optional_prop('sort_desc', False))

            def key_fn(t):
                if sort_key == 'added_at':
                    return t['added_at']
                elif sort_key == 'name':
                    return t['track']['name']
                elif sort_key == 'artist':
                    return t['track']['artists'][0]['name']
                elif sort_key == 'album':
                    return t['track']['album']['name']
                elif sort_key == 'release_date':
                    return t['track']['album']['release_date']
                else:
                    raise ValueError(f'sort node <{self.nid}> unable to find sort key <{sort_key}> in track: {t}')

            return sorted(self.inputs[0].tracks(), key=key_fn, reverse=sort_desc)
        elif self.ntype == 'dedup':
            self.assert_input_count(1)
            tracks_by_uri = {}
            for track in self.inputs[0].tracks():
                uri = track['track']['uri']
                if uri not in tracks_by_uri:
                    tracks_by_uri[uri] = track
            return [track for uri, track in tracks_by_uri.items()]
        else:
            raise ValueError(f"Unsupported type <{self.ntype}> for node <{self.nid}>")


class TemplateNode(Node):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.template_name = self.get_required_prop('template_name')

    def tracks(self):
        raise ValueError(f'Cannot fetch tracks directly from a template node')

    def resolve_template(self):
        if self.template_name == 'combine_sort_dedup_output':
            # Required props: [input_uris or input_nodes], sort_key, output_playlist_name
            node_list = list()
            if self.has_prop('input_uris'):
                for idx, input_uri in enumerate(self.get_required_prop('input_uris')):
                    node_list.append(InputNode(spotipy_client=self.spotipy, node_id=f'{self.nid}_in_{idx}',
                                               type='input', source_type='playlist', uri=input_uri))
                input_node_ids = [node.nid for node in node_list]
            else:
                input_node_ids = self.get_required_prop('input_nodes')
            node_list.append(LogicNode(spotipy_client=self.spotipy, node_id=f'{self.nid}_combine', type='combiner',
                                       inputs=input_node_ids))
            node_list.append(LogicNode(spotipy_client=self.spotipy, node_id=f'{self.nid}_sort', type='sort',
                                       inputs=[f'{self.nid}_combine'],
                                       sort_key=self.get_required_prop('sort_key')))
            node_list.append(LogicNode(spotipy_client=self.spotipy, node_id=f'{self.nid}_dedup', type='dedup',
                                       inputs=[f'{self.nid}_sort']))
            node_list.append(OutputNode(spotipy_client=self.spotipy, node_id=f'{self.nid}', type='output',
                                        inputs=[f'{self.nid}_dedup'],
                                        playlist_name=self.get_required_prop('output_playlist_name')))
            return {node.nid: node for node in node_list}
        if self.template_name == 'time_genre_combiner':
            # Required props: genres, times, <time>_<genre>_uri for all (genre, time), output_name_format
            #    genres - list of genre names
            #    times - list of time period names
            #    <time>_<genre>_uri - playlist uri for the combination of the given time and genre
            #    output_name_format - format string for the output playlist name,
            #                         <GENRE> will be replaced with the genre and <TIME> will be replaced with the time
            node_list = list()
            genres = self.get_required_prop('genres')
            times = self.get_required_prop('times')
            for genre in genres:
                for time in times:
                    node_list.append(InputNode(spotipy_client=self.spotipy, node_id=f'{self.nid}_{time}_{genre}',
                                               type='input', source_type='playlist',
                                               uri=self.get_required_prop(f'{time}_{genre}_uri')))

            def get_output_name(time, genre):
                return re.sub(r'\s+', ' ', self.get_required_prop('output_name_format')
                              .replace('<TIME>', time).replace('<GENRE>', genre)).strip()

            for time in times:
                node_list.append(TemplateNode(spotipy_client=self.spotipy, node_id=f'{self.nid}_{time}_all',
                                              type='template', template_name='combine_sort_dedup_output',
                                              sort_key='added_at', output_playlist_name=get_output_name(time, ''),
                                              input_nodes=[f'{self.nid}_{time}_{genre}' for genre in genres]))
            for genre in genres:
                node_list.append(TemplateNode(spotipy_client=self.spotipy, node_id=f'{self.nid}_{genre}_all',
                                              type='template', template_name='combine_sort_dedup_output',
                                              sort_key='added_at', output_playlist_name=get_output_name('', genre),
                                              input_nodes=[f'{self.nid}_{time}_{genre}' for time in times]))
            node_list.append(TemplateNode(spotipy_client=self.spotipy, node_id=f'{self.nid}_all',
                                          type='template', template_name='combine_sort_dedup_output',
                                          sort_key='added_at', output_playlist_name=get_output_name('All', ''),
                                          input_nodes=[f'{self.nid}_{time}_all' for time in times]))
            return {node.nid: node for node in node_list}
        else:
            raise ValueError(f'Unsupported template name for <{self.nid}>: {self.template_name}')
