from __future__ import annotations

import abc
import functools
import inspect
import re
from datetime import timedelta
from typing import Any, Iterable, cast

import spotipy

from . import utils
from .spotify_client import *
from .utils import VerifyMode

logger = logging.getLogger(__name__)


def _load_nodes_from_dict(spotify_client: SpotifyClient,
                          unresolved_node_list: Iterable[(str, Dict)]) -> Dict[str, Node]:
    return {
        node_id: Node.from_dict(spotify_client, node_id, node_dict)
        for node_id, node_dict in unresolved_node_list
    }


def resolve_node_list(spotify_client: SpotifyClient,
                      unresolved_node_list: Iterable[(str, Dict)]) -> List[Node]:
    node_map_unresolved = _load_nodes_from_dict(spotify_client, unresolved_node_list)
    node_map = node_map_unresolved
    while len([n for n in node_map_unresolved.values() if isinstance(n, TemplateNode)]) > 0:
        node_map = {}
        for node in node_map_unresolved.values():
            for res_nid, res_node in node.resolve_template().items():
                node_map[res_nid] = res_node
        node_map_unresolved = node_map
    for node in node_map.values():
        node.resolve_inputs(node_map)
    node_list = list(node_map.values())
    output_playlist_names = {cast(OutputNode, node).playlist_name()
                             for node in node_list
                             if isinstance(node, OutputNode)}
    spotify_client.current_user_playlists()  # populate the cache of playlist descriptions
    input_playlist_names = {spotify_client.playlist_description(cast(PlaylistNode, node).playlist_uri()).name
                            for node in node_list
                            if isinstance(node, PlaylistNode)}
    intersection = input_playlist_names.intersection(output_playlist_names)
    if len(intersection) != 0:
        raise ValueError(f'Found an invalid scenario definition; the following playlists are both input '
                         f'and output playlists: {intersection}')
    return node_list


class Node(abc.ABC):
    def __init__(self, **kwargs):
        self.spotify: SpotifyClient = kwargs['spotify_client']
        self.nid: str = kwargs['node_id']
        self.__fulldict: Dict = kwargs

    @staticmethod
    def from_dict(spotify_client: SpotifyClient, node_id: str, node_dict: Dict):
        if 'type' not in node_dict:
            raise ValueError(f'Invalid definition for node <{node_id}>; unable to find "type" specifier')
        ntype = node_dict.pop('type')

        def all_subclasses(cls):
            return set(cls.__subclasses__()) \
                .union([s for c in cls.__subclasses__() for s in all_subclasses(c)])
        concrete_node_classes = [nclass for nclass in all_subclasses(Node) if not inspect.isabstract(nclass)]
        matched_node_class = [nclass for nclass in concrete_node_classes if nclass.ntype() == ntype]
        if len(matched_node_class) != 1:
            raise ValueError(f'Found {len(matched_node_class)} node types matching type `{ntype}` from full list: '
                             f'{",".join([cnc.ntype() for cnc in concrete_node_classes])}')
        return matched_node_class[0](spotify_client=spotify_client, node_id=node_id, **node_dict)

    @abc.abstractmethod
    def tracks(self) -> List[Track]:
        pass

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.__fulldict == other.__fulldict
        else:
            raise NotImplementedError

    def __ne__(self, other):
        if isinstance(other, Node):
            return self.__fulldict != other.__fulldict
        else:
            raise NotImplementedError

    def resolve_inputs(self, node_dict: Dict[str, Node]) -> None:
        pass

    def resolve_template(self) -> Dict[str, Node]:
        return {self.nid: self}

    def has_prop(self, prop_key: str):
        return prop_key in self.__fulldict

    def get_required_prop(self, prop_key: str):
        if prop_key not in self.__fulldict:
            raise ValueError(f'Node <{self.nid}> requires prop <{prop_key}> but was not found')
        return self.__fulldict[prop_key]

    @staticmethod
    def _to_saved_track(track: Track) -> SavedTrack:
        if isinstance(track, SavedTrack):
            return track
        else:
            raise ValueError(f'Expecting PlaylistTrack but found {type(track)}')

    def get_optional_prop(self, prop_key: str, default_value):
        return self.__fulldict.get(prop_key, default_value)

    @classmethod
    @abc.abstractmethod
    def ntype(cls):
        pass


class InputNode(Node, abc.ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.track_cache = None

    @abc.abstractmethod
    def _fetch_tracks_impl(self) -> List[Track]:
        pass

    def tracks(self):
        if self.track_cache is None:
            self.track_cache = self._fetch_tracks_impl()
        return self.track_cache


class PlaylistNode(InputNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def ntype(cls):
        return 'playlist'

    def playlist_uri(self):
        return self.get_required_prop('uri')

    def _fetch_tracks_impl(self):
        return self.spotify.playlist(self.playlist_uri()).tracks


class LikedTracksNode(InputNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def ntype(cls):
        return 'liked_tracks'

    def _fetch_tracks_impl(self):
        return self.spotify.saved_tracks()


class AllTracksNode(InputNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def ntype(cls):
        return 'all_tracks'

    def _fetch_tracks_impl(self):
        all_tracks = self.spotify.saved_tracks()
        playlists = self.spotify.current_user_playlists()
        if not bool(self.get_optional_prop('include_dynamic', False)):
            playlists = [p for p in playlists
                         if Constants.AUTOGEN_PLAYLIST_DESCRIPTION not in p.description]
        for playlist_desc in playlists:
            all_tracks.extend(self.spotify.playlist(playlist_desc.uri).tracks)
        return all_tracks


class NonleafNode(Node, abc.ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.input_nids: List[Optional[str]] = kwargs.get('inputs', [kwargs.get('input')])
        if len(self.input_nids) == 1 and self.input_nids[0] is None:
            raise ValueError(f'No input found for node <{self.nid}>. Looked for "input" and "inputs"')
        self.inputs: List[Node] = list()

    def resolve_inputs(self, node_dict: Dict[str, Node]):
        self.inputs = [node_dict[node_id] for node_id in self.input_nids]


class OutputNode(NonleafNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def ntype(cls):
        return 'output'

    def tracks(self):
        if len(self.inputs) != 1:
            raise ValueError(f'Unexpected number of inputs for output node <{self.nid}>')
        return self.inputs[0].tracks()

    def playlist_name(self) -> str:
        return self.get_required_prop('playlist_name')

    def create_or_update(self):
        is_updated = False
        playlist_list = self.spotify.current_user_playlists()
        matching_playlist_uris = [pl.uri for pl in playlist_list if pl.name == self.playlist_name()]
        is_public = bool(self.get_optional_prop('public', False))
        if len(matching_playlist_uris) > 1:
            raise ValueError(f'Found {len(matching_playlist_uris)} with name "{self.playlist_name()}". '
                             f'Expected to find 1 or none. Refusing to update any of them.')
        elif len(matching_playlist_uris) == 1:
            playlist_uri = matching_playlist_uris[0]
            playlist = self.spotify.playlist(playlist_uri)
            if playlist.public != is_public or Constants.AUTOGEN_PLAYLIST_DESCRIPTION not in playlist.description:
                self.spotify.playlist_change_details(playlist.oid,
                                                     public=is_public,
                                                     description=Constants.AUTOGEN_PLAYLIST_DESCRIPTION)
            existing_track_uris = [track.uri for track in playlist.tracks]
        else:
            logging.info(f'Creating new playlist `{self.playlist_name()}`')
            playlist = self.spotify.create_playlist(
                self.playlist_name(), Constants.AUTOGEN_PLAYLIST_DESCRIPTION, is_public, False)
            existing_track_uris = list()
        snapshot_id = playlist.snapshot_id

        # create set of new/updated/removed/etc. tracks
        expected_output_track_uris = [track.uri for track in self.tracks()]

        # Step 1: Remove tracks that shouldn't be there at all
        expected_output_track_uri_dict: Dict[str, int] = dict()
        for track in self.tracks():
            expected_output_track_uri_dict[track.uri] = expected_output_track_uri_dict.get(track.uri, 0) + 1
        required_removals: List[(str, int)] = list()
        remaining_output_track_uri_dict = expected_output_track_uri_dict.copy()
        expected_output_track_uris_after_removals: List[str] = list()
        for idx, uri in enumerate(existing_track_uris):
            remaining = remaining_output_track_uri_dict.get(uri, 0)
            if remaining == 0:
                required_removals.append((uri, idx))
            else:
                remaining_output_track_uri_dict[uri] = remaining - 1
                expected_output_track_uris_after_removals.append(uri)

        if len(required_removals) > 0:
            logger.debug(f'Playlist [{self.playlist_name()}]: Removing tracks: {required_removals}')
            self.spotify.playlist_remove_specific_occurrences_of_items(
                playlist.uri, required_removals, snapshot_id=playlist.snapshot_id)
            is_updated = True
            self.verify_playlist_contents(expected_output_track_uris_after_removals, playlist.uri, 'item removal')

        # Step 2: Add new tracks
        existing_track_uri_dict: Dict[str, int] = dict()
        for uri in existing_track_uris:
            existing_track_uri_dict[uri] = existing_track_uri_dict.get(uri, 0) + 1
        required_addition_uris: List[str] = list()
        remaining_existing_track_uri_dict = existing_track_uri_dict.copy()
        for uri in expected_output_track_uris:
            remaining = remaining_existing_track_uri_dict.get(uri, 0)
            if remaining == 0:
                required_addition_uris.append(uri)
            else:
                remaining_existing_track_uri_dict[uri] = remaining - 1

        if len(required_addition_uris) > 0:
            logger.debug(f'Playlist [{self.playlist_name()}]: Adding tracks: {required_addition_uris}')
            snapshot_id = self.spotify.playlist_add_items(playlist.uri, required_addition_uris)
            expected_ordering = expected_output_track_uris_after_removals + required_addition_uris
            is_updated = True
            self.verify_playlist_contents(expected_ordering, playlist.uri, 'item addition')

        # Step 3: Reorder tracks currently in the playlist to match the expected order
        current_track_uris = expected_output_track_uris_after_removals + required_addition_uris
        if len(current_track_uris) != len(expected_output_track_uris):
            raise ValueError(f'Expected to find {len(expected_output_track_uris)} track URIs '
                             f'but found only {len(current_track_uris)}')
        elif current_track_uris != expected_output_track_uris:
            while current_track_uris != expected_output_track_uris:
                target_idx, target_uri = next((target_idx, uri)
                                              for target_idx, uri in enumerate(expected_output_track_uris)
                                              if current_track_uris[target_idx] != uri)
                start_idx = current_track_uris.index(target_uri)
                logger.debug(f'Playlist [{self.playlist_name()}]: Inserting pos {start_idx} into pos {target_idx} '
                             f'(target song uri <{target_uri}>)')
                # TODO attempt to group ranges to reduce API call volume
                try:
                    snapshot_id = self.spotify.playlist_reorder_items(
                        playlist.uri, start_idx, target_idx, snapshot_id=snapshot_id)
                except (KeyError, spotipy.SpotifyException) as se:
                    logger.error(f'Encountered error while attempting to reorder items. playlist_uri={playlist.uri}, '
                                 f'start_idx={start_idx}, target_idx={target_idx}, snapshot_id={snapshot_id}',
                                 exc_info=se)
                    raise se
                current_track_uris.insert(target_idx, current_track_uris.pop(start_idx))
            is_updated = True
            self.verify_playlist_contents(expected_output_track_uris, playlist.uri, 'reordering')

        if is_updated:
            logging.info(f'Updated playlist `{self.playlist_name()}` to reflect new changes, will verify output.')
            self.verify_playlist_contents(expected_output_track_uris, playlist.uri, 'updates')
            new_desc = Constants.AUTOGEN_PLAYLIST_DESCRIPTION + \
                f' (last updated {datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M%z")})'
            self.spotify.playlist_change_details(playlist.uri, description=new_desc)
        else:
            logging.info(f'Playlist `{self.playlist_name()}` was not updated because no changes were detected.')

    def verify_playlist_contents(self, expected_uris: List[str], playlist_uri: str, action_description: str,
                                 is_end: bool = False):
        if utils.global_conf.verify_mode == VerifyMode.INCREMENTAL \
                or (utils.global_conf.verify_mode == VerifyMode.END and is_end):
            playlist = self.spotify.playlist(playlist_uri, force_reload=True)
            uris = [track.uri for track in playlist.tracks]
            if uris != expected_uris:
                raise ValueError(f'Playlist {action_description} for <{self.nid}> resulted in unexpected contents.\n'
                                 f'Expected {len(expected_uris)} items and found {len(uris)}.\n'
                                 f'Found missing items: {set(expected_uris) - set(uris)}.\n'
                                 f'Found unexpected items: {set(uris) - set(expected_uris)}.\n'
                                 f'Expected items: {expected_uris}.\nFound items: {uris}.')


class LogicNode(NonleafNode, abc.ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _assert_input_count(self, expected_count):
        if len(self.inputs) != expected_count:
            raise ValueError(f'Nodes of type {self.ntype()} are expected to have {expected_count} inputs, but '
                             f'node <{self.nid}> had {len(self.inputs)}')

    def _get_single_input_tracks(self) -> List[Track]:
        self._assert_input_count(1)
        return self.inputs[0].tracks()


class CombinerNode(LogicNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def ntype(cls):
        return 'combiner'

    def tracks(self):
        return functools.reduce(lambda l1, l2: l1 + l2, map(lambda i: i.tracks(), self.inputs))


class SortNode(LogicNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def ntype(cls):
        return 'sort'

    def tracks(self):
        sort_key = self.get_required_prop('sort_key')
        sort_desc = bool(self.get_optional_prop('sort_desc', False))

        def key_fn(t: Track):
            if sort_key == 'time_added':
                return Node._to_saved_track(t).added_at
            elif sort_key == 'name':
                return t.name
            elif sort_key == 'artist':
                return t.artists[0].name
            elif sort_key == 'album':
                return t.album.name
            elif sort_key == 'release_date':
                return t.album.release_date
            else:
                raise ValueError(f'sort node <{self.nid}> unable to find sort key <{sort_key}> in track: {t}')

        return sorted(self._get_single_input_tracks(), key=key_fn, reverse=sort_desc)


class FilterNode(LogicNode, abc.ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def tracks(self):
        return [track for track in self._get_single_input_tracks() if self.track_predicate(track)]

    @abc.abstractmethod
    def track_predicate(self, track):
        pass


class FilterEvalNode(FilterNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def ntype(cls):
        return 'filter_eval'

    def tracks(self):
        return [track for track in self._get_single_input_tracks() if self.track_predicate(track)]

    def track_predicate(self, track):
        eval(self.get_required_prop('predicate'), {'t': track})


class TimeBasedFilterNode(FilterNode, abc.ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abc.abstractmethod
    def get_time(self, track: Track):
        pass

    def track_predicate(self, track: Track):
        track_time = self.get_time(track)
        if self.has_prop('days_ago'):
            if self.has_prop('added_after') or self.has_prop('added_before'):
                raise ValueError(f'Node <{self.nid}> cannot have both relative and fixed date specifiers')
            cutoff_time = (datetime.now() - timedelta(days=int(self.get_required_prop('days_ago'))))
        else:
            cutoff_time = parser.isoparse(self.get_required_prop('cutoff_time'))
        if self.get_optional_prop('keep_before', False):
            return cutoff_time > track_time
        else:
            return track_time >= cutoff_time


class AddedAtFilterNode(TimeBasedFilterNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def ntype(cls):
        return 'filter_time_added'

    def get_time(self, track: Track):
        return Node._to_saved_track(track).added_at


class ReleaseDateFilterNode(TimeBasedFilterNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def ntype(cls):
        return 'filter_release_date'

    def get_time(self, track: Track):
        return track.album.release_date


class DeduplicateNode(LogicNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def ntype(cls):
        return 'dedup'

    def tracks(self):
        tracks_by_uri = {}
        for track in self._get_single_input_tracks():
            if track.uri not in tracks_by_uri:
                tracks_by_uri[track.uri] = track
        return [track for uri, track in tracks_by_uri.items()]


class LikedNode(LogicNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._track_cache = None

    @classmethod
    def ntype(cls):
        return 'is_liked'

    def tracks(self):
        if self._track_cache is None:
            self._assert_input_count(1)
            input_tracks = self._get_single_input_tracks()
            matches = self.spotify.saved_tracks_contains([track.uri for track in input_tracks])
            self._track_cache = [track for (track, matched) in zip(input_tracks, matches) if matched]
        return self._track_cache


class TemplateNode(Node, abc.ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def tracks(self):
        raise ValueError(f'Cannot fetch tracks directly from a template node')


class DynamicTemplateNode(TemplateNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def ntype(cls):
        return 'dynamic_template'

    def copy_replace(self, obj, var_map: Dict[str, Any]):
        if isinstance(obj, Dict):
            return {
                self.copy_replace(k, var_map): self.copy_replace(v, var_map)
                for k, v in obj.items()
            }
        elif isinstance(obj, List):
            return [self.copy_replace(ele, var_map) for ele in obj]
        elif isinstance(obj, str):
            varmatch = re.fullmatch(r'\{([^{}]+)}', obj)
            if varmatch and varmatch.group(1) in var_map:
                return var_map[varmatch.group(1)]
            else:
                out = obj
                for (var, val) in var_map.items():
                    varstr = '{' + var + '}'
                    if varstr in out:
                        if not isinstance(val, str):
                            raise ValueError(f'Variable {var} is used as a string but found value '
                                             f'of type {type(val)}: {val}')
                        out = out.replace(varstr, val)
                return out
        elif type(obj) in (int, float, bool):
            return obj
        else:
            raise ValueError(f'Unsupported type ({type(obj)}): {obj}')

    def resolve_template(self):
        # Required props: template, instances
        # template is a dictionary of node_id -> node definition, the same as a top-level
        #   node definition. However, '{var_name}' can appear anywhere in the definition
        #   (including, and necessarily, in the node ID). Multiple variables can be used,
        #   even in the same value.
        # instances is a list of dict where each key is a variable name (such as
        #   var_name above) and the value is the value for that variable. A copy of
        #   the nodes from `template` will be instantiated for each list item, and
        #   all variables will be substituted by their values.
        template_nodes: Dict[str, Any] = self.get_required_prop('template')
        template_instances: List[Dict[str, Any]] = self.get_required_prop('instances')
        node_dict = {}

        for var_map in template_instances:
            instance_map = self.copy_replace(template_nodes, var_map)
            node_dict.update(_load_nodes_from_dict(self.spotify, instance_map.items()))

        return node_dict


class CombineSortDedupOutput(TemplateNode):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def ntype(cls):
        return 'combine_sort_dedup_output'

    def resolve_template(self):
        # Required props: [input_uris or input_nodes], sort_key, output_playlist_name
        # Optional props: [sort_desc]
        node_list = list()
        if self.has_prop('input_uris'):
            for idx, input_uri in enumerate(self.get_required_prop('input_uris')):
                node_list.append(PlaylistNode(spotify_client=self.spotify,
                                              node_id=f'{self.nid}_in_{idx}',
                                              uri=input_uri))
            input_node_ids = [node.nid for node in node_list]
        else:
            input_node_ids = self.get_required_prop('input_nodes')
        node_list.append(CombinerNode(spotify_client=self.spotify, node_id=f'{self.nid}_combine',
                                      inputs=input_node_ids))
        node_list.append(SortNode(spotify_client=self.spotify, node_id=f'{self.nid}_sort',
                                  inputs=[f'{self.nid}_combine'],
                                  sort_key=self.get_required_prop('sort_key'),
                                  sort_desc=self.get_optional_prop('sort_desc', False)))
        node_list.append(DeduplicateNode(spotify_client=self.spotify, node_id=f'{self.nid}_dedup',
                                         inputs=[f'{self.nid}_sort']))
        node_list.append(OutputNode(spotify_client=self.spotify, node_id=f'{self.nid}',
                                    inputs=[f'{self.nid}_dedup'],
                                    playlist_name=self.get_required_prop('output_playlist_name')))
        return {node.nid: node for node in node_list}
