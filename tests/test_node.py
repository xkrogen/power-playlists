import itertools
from itertools import chain
from typing import cast

import pytest

import testutil
from dynamicplaylist import nodes
from dynamicplaylist.nodes import InputNode, OutputNode
from test_mocks import MockClient


def get_all_permutations_as_str(input_list):
    input_list = input_list.split(',') if type(input_list) == str else input_list
    all_combinations_nested = [itertools.combinations(['t1', 't2', 't3', 't4', 't5'], r)
                               for r in range(1, len(input_list) + 1)]
    all_permutations_nested = [itertools.permutations(combo)
                               for combo in chain.from_iterable(all_combinations_nested)]
    return [','.join(perm) for perm in chain.from_iterable(all_permutations_nested)]


class TestNode:

    def test_input_node_pagination_and_caching(self):
        expected_track_uris = [f'track{i}' for i in range(0, 500)]
        mock_client = MockClient(expected_track_uris)
        in_node = InputNode(spotipy_client=mock_client, node_id='test', type='input',
                            source_type='playlist', uri='test_pl_uri')

        output_tracks = in_node.tracks()
        assert len(output_tracks) == len(expected_track_uris)
        assert [track['track']['uri'] for track in output_tracks] == expected_track_uris
        assert mock_client.api_call_count == 9

        assert len(in_node.tracks()) == len(expected_track_uris)
        assert len(in_node.tracks()) == len(expected_track_uris)
        assert mock_client.api_call_count == 9

    def test_playlist_fetch_pagination(self):
        playlists = [{
            'name': f'pl_{i}', 'uri': f'pl_uri_{i}', 'tracks': {'total': 0, 'items': list()},
            'public': False, 'description': 'bar', 'snapshot_id': 'ignored', 'id': str(i)
        } for i in range(0, 500)]
        expected_output_list = ['t1', 't2', 't3']
        playlists[450]['tracks']['items'] = [testutil.create_track_dict(uri) for uri in expected_output_list]
        playlists[450]['tracks']['total'] = 3
        mock_client = MockClient('t0', playlists)
        out_node = OutputNode(spotipy_client=mock_client, node_id='test', type='output', inputs=list(),
                              playlist_name='pl_450')
        out_node.tracks = lambda: [testutil.create_track_dict(uri) for uri in expected_output_list]
        out_node.create_or_update()

        # 10 API calls for the playlists, 1 to fetch the tracks, 1 for update description, 1 for update track list
        assert mock_client.api_call_count == 13
        testutil.assert_playlist_uris(mock_client, 'pl_uri_450', expected_output_list)

    @pytest.mark.parametrize("expected_outputs", get_all_permutations_as_str('t1,t2,t3,t4,t5'))
    def test_playlist_output_diff_logic(self, expected_outputs):
        expected_output_list = expected_outputs.split(',') if type(expected_outputs) == str else expected_outputs
        mock_client = MockClient('t1,t2,t3')
        out_node = OutputNode(spotipy_client=mock_client, node_id='test', type='output', inputs=list(),
                              playlist_name='test_pl')
        out_node.tracks = lambda: [testutil.create_track_dict(uri) for uri in expected_output_list]
        out_node.create_or_update()

        testutil.assert_playlist_uris(mock_client, 'test_pl_uri', expected_output_list)

    # TODO re-enable this test once duplicates are supported
    @pytest.mark.skip
    @pytest.mark.parametrize("expected_outputs", get_all_permutations_as_str('t1,t1,t2,t1,t3'))
    def test_playlist_output_diff_logic_with_duplicates(self, expected_outputs):
        expected_output_list = expected_outputs.split(',') if type(expected_outputs) == str else expected_outputs
        mock_client = MockClient('t1,t3,t3')
        out_node = OutputNode(spotipy_client=mock_client, node_id='test', type='output', inputs=list(),
                              playlist_name='test_pl')
        out_node.tracks = lambda: [testutil.create_track_dict(uri) for uri in expected_output_list]
        out_node.create_or_update()

        testutil.assert_playlist_uris(mock_client, 'test_pl_uri', expected_output_list)

    def test_playlist_add_items_pagination(self):
        expected_output_list = [f't_{i}' for i in range(0, 200)]
        mock_client = MockClient('t_0,t_1,t_2')
        out_node = OutputNode(spotipy_client=mock_client, node_id='test', type='output', inputs=list(),
                              playlist_name='test_pl')
        out_node.tracks = lambda: [testutil.create_track_dict(uri) for uri in expected_output_list]
        out_node.create_or_update()

        assert mock_client.api_call_count == 10
        testutil.assert_playlist_uris(mock_client, 'test_pl_uri', expected_output_list)

    def test_playlist_remove_items_pagination(self):
        expected_output_list = ['t0', 't1', 't2']
        mock_client = MockClient([f't{i}' for i in range(0, 200)])
        out_node = OutputNode(spotipy_client=mock_client, node_id='test', type='output', inputs=list(),
                              playlist_name='test_pl')
        out_node.tracks = lambda: [testutil.create_track_dict(uri) for uri in expected_output_list]
        out_node.create_or_update()

        assert mock_client.api_call_count == 10
        testutil.assert_playlist_uris(mock_client, 'test_pl_uri', expected_output_list)

    def test_resolve_node_list_valid(self):
        playlists = [{
            'name': f'pl_{i}', 'uri': f'pl_uri_{i}', 'tracks': {'total': 0, 'items': list()},
            'public': False, 'description': 'bar', 'snapshot_id': 'ignored', 'id': str(i)
        } for i in range(0, 5)]
        mock_client = MockClient([], playlists)
        input_nodes = [
            ('in1', {'type': 'input', 'source_type': 'playlist', 'uri': 'pl_uri_1'}),
            ('in2', {'type': 'input', 'source_type': 'playlist', 'uri': 'pl_uri_2'}),
            ('dedup', {'type': 'dedup', 'inputs': ['in1']}),
            ('out1', {'type': 'output', 'playlist_name': 'pl_3', 'inputs': ['dedup']}),
        ]
        resolved = nodes.resolve_node_list(mock_client, input_nodes)
        assert len(resolved) == 4
        out_nodes = [cast(OutputNode, n) for n in resolved if type(n) == OutputNode]
        assert len(out_nodes) == 1
        assert out_nodes[0].input_node().ntype == 'dedup'

    def test_resolve_node_list_invalid(self):
        playlists = [{
            'name': f'pl_{i}', 'uri': f'pl_uri_{i}', 'tracks': {'total': 0, 'items': list()},
            'public': False, 'description': 'bar', 'snapshot_id': 'ignored', 'id': str(i)
        } for i in range(0, 5)]
        mock_client = MockClient([], playlists)
        input_nodes = [
            ('in1', {'type': 'input', 'source_type': 'playlist', 'uri': 'pl_uri_1'}),
            ('in2', {'type': 'input', 'source_type': 'playlist', 'uri': 'pl_uri_2'}),
            ('dedup', {'type': 'dedup', 'inputs': ['in1']}),
            ('out1', {'type': 'output', 'playlist_name': 'pl_2', 'inputs': ['dedup']}),
        ]
        try:
            nodes.resolve_node_list(mock_client, input_nodes)
            assert False
        except ValueError as err:
            assert 'invalid scenario definition' in str(err)

    def test_resolve_node_list_template(self):
        playlists = [{
            'name': f'pl_{i}', 'uri': f'pl_uri_{i}', 'tracks': {'total': 0, 'items': list()},
            'public': False, 'description': 'bar', 'snapshot_id': 'ignored', 'id': str(i)
        } for i in range(0, 5)]
        mock_client = MockClient([], playlists)
        input_nodes = [
            ('template', {
                'type': 'template',
                'template_name': 'combine_sort_dedup_output',
                'input_uris': ['pl_uri_1', 'pl_uri_2'],
                'sort_key': 'added_at',
                'output_playlist_name': 'out_pl_name',
            }),
        ]
        resolved = nodes.resolve_node_list(spotipy_client=mock_client, unresolved_node_list=input_nodes)
        assert len(resolved) == 6
        for ntype in ['dedup', 'sort', 'combiner', 'output']:
            assert sum([1 for n in resolved if n.ntype == ntype]) == 1
        assert sum([1 for n in resolved if type(n) == InputNode]) == 2
        assert [cast(OutputNode, n) for n in resolved if type(n) == OutputNode][0].playlist_name() == 'out_pl_name'
