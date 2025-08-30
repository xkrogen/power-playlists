import copy
import random
import string
from collections import defaultdict
from typing import Dict, List

import pytest
import spotipy

import testutil


class MockClient(spotipy.Spotify):

    def __init__(self, track_uri_list, other_playlists: List[Dict[str, str]] = None):
        if type(track_uri_list) == str:
            track_uri_list = track_uri_list.split(',')
        self.playlists = [testutil.create_playlist_dict(
            'test_pl_uri',
            [testutil.create_track_dict(uri) for uri in track_uri_list],
            'test_pl')
        ]
        if other_playlists is not None:
            self.playlists.extend(other_playlists)
        self.api_call_counts = defaultdict(lambda: 0)

    def _get_playlist(self, uri=None, playlist_id=None) -> Dict:
        if uri is not None:
            return [playlist for playlist in self.playlists if playlist['uri'] == uri][0]
        elif playlist_id is not None:
            return [playlist for playlist in self.playlists if playlist['id'] == playlist_id][0]
        else:
            raise ValueError('Must supply either uri or playlist_id')

    def current_user(self):
        return testutil.get_user_dict('test_pl_owner')

    def current_user_playlists(self, offset=0, limit=50):
        self.__increment_call_count('current_user_playlists')
        return {'items': self.playlists[offset:offset+limit], 'total': len(self.playlists)}

    def __get_playlist_page(self, uri, limit, offset):
        playlist_copy = copy.deepcopy(self._get_playlist(uri=uri))
        playlist_copy['tracks']['items'] = playlist_copy['tracks']['items'][offset:offset+limit]
        playlist_copy['tracks']['offset'] = offset
        playlist_copy['tracks']['limit'] = limit
        return playlist_copy

    def __increment_call_count(self, api_name: str):
        self.api_call_counts[api_name] = self.api_call_counts[api_name] + 1

    def playlist(self, uri, fields=None, market=None, additional_types=("track",)):
        self.__increment_call_count('playlist')
        return self.__get_playlist_page(uri, 100, 0)

    def playlist_items(self, playlist_id, fields=None, limit=100, offset=0, market=None,
                       additional_types=("track", "episode")):
        self.__increment_call_count('playlist_items')
        return self.__get_playlist_page(playlist_id, limit, offset)['tracks']

    def playlist_remove_specific_occurrences_of_items(self, uri, removal_dict_list, snapshot_id=None):
        self.__increment_call_count('playlist_remove_specific_occurrences_of_items')
        playlist = self._get_playlist(uri=uri)
        items = playlist['tracks']['items']
        removal_cnt = 0
        removal_tuples = [(removal_dict['uri'], removal_dict['positions'][0]) for removal_dict in removal_dict_list]
        removal_tuples.sort(key=lambda tup: tup[1])  # sort by pos
        for uri, pos in removal_tuples:
            pos_corrected = pos - removal_cnt
            if items[pos_corrected]['track']['uri'] != uri:
                raise ValueError(f'Found uri <{items[pos_corrected]["track"]["uri"]}> at position <{pos_corrected}> '
                                 f'but expected <{uri}>. Full list: <{items}>')
            items.pop(pos_corrected)
            removal_cnt += 1
        playlist['tracks']['total'] = len(items)
        return {'snapshot_id': 'ignored'}

    def playlist_reorder_items(self, uri, range_start, insert_before, range_length=1, snapshot_id=None):
        self.__increment_call_count('playlist_reorder_items')
        playlist = self._get_playlist(uri=uri)
        items: List = playlist['tracks']['items']
        if range_start == insert_before:
            return {'snapshot_id': 'ignored'}  # no-op
        if range_length != 1:
            raise ValueError('range_length != 1 not yet supported')
        items_prev = items[0:insert_before] if insert_before != 0 else list()
        items_after = items[insert_before:] if insert_before != len(items) else list()
        if range_start < insert_before:
            popped: str = items_prev.pop(range_start)
        else:
            popped: str = items_after.pop(range_start - insert_before)
        playlist['tracks']['items'] = items_prev + [popped] + items_after
        return {'snapshot_id': 'ignored'}

    def playlist_add_items(self, uri, item_uris, position=None, snapshot_id=None):
        self.__increment_call_count('playlist_add_items')
        playlist = self._get_playlist(uri=uri)
        curr_items: List = playlist['tracks']['items']
        position = len(curr_items) if position is None else position
        if position > len(curr_items):
            raise ValueError(f'Received invalid position <{position}> for playlist of length {len(curr_items)}')
        for (idx, uri) in enumerate(item_uris):
            curr_items.insert(position + idx, testutil.create_track_dict(uri))
        playlist['tracks']['total'] = len(curr_items)
        return {'snapshot_id': 'ignored'}

    def playlist_change_details(self, playlist_id, name=None, public=None, collaborative=None, description=None):
        self.__increment_call_count('playlist_change_details')
        playlist = self._get_playlist(playlist_id=playlist_id)
        if public is not None:
            playlist['public'] = public
        if description is not None:
            playlist['description'] = description

    def user_playlist_create(self, user_id, name, public=True, collaborative=False, description=""):
        assert user_id == self.current_user()['id']
        uri = ''.join(random.choice(string.ascii_lowercase) for ignored in range(30))
        pdict = testutil.create_playlist_dict(uri, list(), name)
        self.playlists.append(pdict)
        return pdict

    def __del__(self):
        pass


class TestMockClient:
    @pytest.mark.parametrize("range_start,insert_before,expected_outputs", [
        (1, 1, 't1,t2,t3,t4'),
        (1, 2, 't1,t2,t3,t4'),
        (1, 0, 't2,t1,t3,t4'),
        (1, 3, 't1,t3,t2,t4'),
        (3, 1, 't1,t4,t2,t3'),
        (0, 3, 't2,t3,t1,t4'),
        (1, 4, 't1,t3,t4,t2'),
    ])
    def test_reorder_items(self, range_start, insert_before, expected_outputs):
        expected_output_list = expected_outputs.split(',')
        mock_client = MockClient('t1,t2,t3,t4')
        mock_client.playlist_reorder_items('test_pl_uri', range_start, insert_before)
        testutil.assert_playlist_uris(mock_client, 'test_pl_uri', expected_output_list)

    @pytest.mark.parametrize("position,new_items,expected_outputs", [
        (3, 't4', 't1,t2,t3,t4'),
        (0, 't4', 't4,t1,t2,t3'),
        (1, 't4', 't1,t4,t2,t3'),
        (2, 't4,t5', 't1,t2,t4,t5,t3'),
        (3, 't4,t5,t6', 't1,t2,t3,t4,t5,t6'),
    ])
    def test_add_items(self, position, new_items, expected_outputs):
        mock_client = MockClient('t1,t2,t3')
        mock_client.playlist_add_items('test_pl_uri', new_items.split(','), position)
        testutil.assert_playlist_uris(mock_client, 'test_pl_uri', expected_outputs.split(','))

    def test_add_items_invalid(self):
        mock_client = MockClient('t1,t2,t3')
        try:
            mock_client.playlist_add_items('test_pl_uri', ['t4'], 10)
            assert False
        except ValueError as err:
            assert 'invalid position' in str(err)
