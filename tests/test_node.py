import itertools
import math
from itertools import chain
from typing import cast, Dict

import pytest
import testutil
from powerplaylists import nodes, utils
from powerplaylists.nodes import (
    PlaylistNode,
    OutputNode,
    DeduplicateNode,
    LikedNode,
    CombinerNode,
    AllTracksNode,
    LimitNode,
)
from powerplaylists.utils import AppConfig, VerifyMode, Constants
from powerplaylists.spotify_client import SpotifyClient, PlaylistTrack
from test_mocks import MockClient

# Import issues have been resolved - tests are now enabled


def get_all_permutations_as_str(input_list):
    input_list = input_list.split(",") if type(input_list) == str else input_list
    all_combinations_nested = [
        itertools.combinations(["t1", "t2", "t3", "t4", "t5"], r) for r in range(1, len(input_list) + 1)
    ]
    all_permutations_nested = [itertools.permutations(combo) for combo in chain.from_iterable(all_combinations_nested)]
    return [",".join(perm) for perm in chain.from_iterable(all_permutations_nested)]


class TestNode:
    @pytest.fixture(autouse=True)
    def set_global_confs(self):
        self.app_config = AppConfig()
        old = utils.global_conf
        utils.global_conf = self.app_config
        utils.global_conf.verify_mode = VerifyMode.INCREMENTAL
        utils.global_conf.client_id = "disabled_for_tests"
        utils.cache_dir = "cache"
        utils.log_file_path = "test.log"
        yield
        utils.global_conf = old

    def get_nocache_client(self, mock_client: MockClient):
        return SpotifyClient(self.app_config, mock_client, enable_cache=False)

    def test_input_node_pagination_and_caching(self):
        expected_track_uris = [f"track{i}" for i in range(0, 500)]
        mock_client = MockClient(expected_track_uris)
        in_node = PlaylistNode(spotify_client=self.get_nocache_client(mock_client), node_id="test", uri="test_pl_uri")

        output_tracks = in_node.tracks()
        assert len(output_tracks) == len(expected_track_uris)
        assert [track.uri for track in output_tracks] == expected_track_uris
        assert mock_client.api_call_counts["playlist"] == 1
        assert mock_client.api_call_counts["playlist_items"] == (500 - 100) / Constants.PAGINATION_LIMIT

        assert len(in_node.tracks()) == len(expected_track_uris)
        assert len(in_node.tracks()) == len(expected_track_uris)
        assert mock_client.api_call_counts["playlist"] == 1
        assert mock_client.api_call_counts["playlist_items"] == (500 - 100) / Constants.PAGINATION_LIMIT

    def test_playlist_fetch_pagination(self):
        playlists = [testutil.create_empty_playlist_dict(f"pl_uri_{i}") for i in range(0, 500)]
        expected_output_list = ["t1", "t2", "t3"]
        playlists[450]["tracks"]["items"] = [testutil.create_track_dict(uri) for uri in expected_output_list]
        playlists[450]["tracks"]["total"] = 3
        mock_client = MockClient("t0", playlists)
        out_node = OutputNode(
            spotify_client=self.get_nocache_client(mock_client), node_id="test", inputs=list(), playlist_name="pl_450"
        )
        out_node.tracks = lambda: [PlaylistTrack(testutil.create_track_dict(uri)) for uri in expected_output_list]
        out_node.create_or_update()

        # MockClient comes with 1 playlist by default so total playlists is 501
        assert mock_client.api_call_counts["current_user_playlists"] == math.ceil(501 / Constants.PAGINATION_LIMIT)
        testutil.assert_playlist_uris(mock_client, "pl_uri_450", expected_output_list)

    @pytest.mark.parametrize("expected_outputs", get_all_permutations_as_str("t1,t2,t3,t4,t5"))
    def test_playlist_output_diff_logic(self, expected_outputs):
        expected_output_list = expected_outputs.split(",") if type(expected_outputs) == str else expected_outputs
        mock_client = MockClient("t1,t2,t3")
        out_node = OutputNode(
            spotify_client=self.get_nocache_client(mock_client), node_id="test", inputs=list(), playlist_name="test_pl"
        )
        out_node.tracks = lambda: [PlaylistTrack(testutil.create_track_dict(uri)) for uri in expected_output_list]
        out_node.create_or_update()

        testutil.assert_playlist_uris(mock_client, "test_pl_uri", expected_output_list)

    @pytest.mark.parametrize("expected_outputs", get_all_permutations_as_str("t1,t1,t2,t1,t3"))
    def test_playlist_output_diff_logic_with_duplicates(self, expected_outputs):
        expected_output_list = expected_outputs.split(",") if type(expected_outputs) == str else expected_outputs
        mock_client = MockClient("t1,t3,t3")
        out_node = OutputNode(
            spotify_client=self.get_nocache_client(mock_client), node_id="test", inputs=list(), playlist_name="test_pl"
        )
        out_node.tracks = lambda: [PlaylistTrack(testutil.create_track_dict(uri)) for uri in expected_output_list]
        out_node.create_or_update()

        testutil.assert_playlist_uris(mock_client, "test_pl_uri", expected_output_list)

    def test_playlist_add_items_pagination(self):
        expected_output_list = [f"t_{i}" for i in range(0, 200)]
        mock_client = MockClient("t_0,t_1,t_2")
        out_node = OutputNode(
            spotify_client=self.get_nocache_client(mock_client), node_id="test", inputs=list(), playlist_name="test_pl"
        )
        out_node.tracks = lambda: [PlaylistTrack(testutil.create_track_dict(uri)) for uri in expected_output_list]
        out_node.create_or_update()

        assert mock_client.api_call_counts["playlist_add_items"] == 200 / Constants.PAGINATION_LIMIT
        testutil.assert_playlist_uris(mock_client, "test_pl_uri", expected_output_list)

    def test_playlist_remove_items_pagination(self):
        expected_output_list = ["t0", "t1", "t2"]
        mock_client = MockClient([f"t{i}" for i in range(0, 200)])
        out_node = OutputNode(
            spotify_client=self.get_nocache_client(mock_client), node_id="test", inputs=list(), playlist_name="test_pl"
        )
        out_node.tracks = lambda: [PlaylistTrack(testutil.create_track_dict(uri)) for uri in expected_output_list]
        out_node.create_or_update()

        assert mock_client.api_call_counts["playlist_remove_specific_occurrences_of_items"] == 5
        testutil.assert_playlist_uris(mock_client, "test_pl_uri", expected_output_list)

    def test_resolve_node_list_valid(self):
        playlists = [testutil.create_empty_playlist_dict(f"pl_uri_{i}") for i in range(0, 5)]
        mock_client = MockClient([], playlists)
        input_nodes = [
            ("in1", {"type": "playlist", "uri": "pl_uri_1"}),
            ("in2", {"type": "playlist", "uri": "pl_uri_2"}),
            ("dedup", {"type": "dedup", "input": "in1"}),
            ("out1", {"type": "output", "playlist_name": "pl_3", "inputs": ["dedup"]}),
        ]
        resolved = nodes.resolve_node_list(self.get_nocache_client(mock_client), input_nodes)
        assert len(resolved) == 4
        out_nodes = [cast(OutputNode, n) for n in resolved if type(n) == OutputNode]
        assert len(out_nodes) == 1
        assert out_nodes[0].inputs[0].ntype() == "dedup"

    def test_resolve_node_list_invalid(self):
        playlists = [testutil.create_playlist_dict(f"pl_uri_{i}", list(), f"pl_{i}") for i in range(0, 5)]
        mock_client = MockClient([], playlists)
        input_nodes = [
            ("in1", {"type": "playlist", "uri": "pl_uri_1"}),
            ("in2", {"type": "playlist", "uri": "pl_uri_2"}),
            ("dedup", {"type": "dedup", "input": "in1"}),
            ("out1", {"type": "output", "playlist_name": "pl_2", "inputs": ["dedup"]}),
        ]
        try:
            nodes.resolve_node_list(self.get_nocache_client(mock_client), input_nodes)
            assert False
        except ValueError as err:
            assert "invalid scenario definition" in str(err)

    def test_resolve_node_list_template(self):
        playlists = [testutil.create_empty_playlist_dict(f"pl_uri_{i}") for i in range(0, 5)]
        mock_client = MockClient([], playlists)
        input_nodes = [
            (
                "template",
                {
                    "type": "combine_sort_dedup_output",
                    "input_uris": ["pl_uri_1", "pl_uri_2"],
                    "sort_key": "added_at",
                    "output_playlist_name": "out_pl_name",
                },
            ),
        ]
        resolved = nodes.resolve_node_list(
            spotify_client=self.get_nocache_client(mock_client), unresolved_node_list=input_nodes
        )
        assert len(resolved) == 6
        for ntype in ["dedup", "sort", "combiner", "output"]:
            assert sum([1 for n in resolved if n.ntype() == ntype]) == 1
        assert sum([1 for n in resolved if type(n) == PlaylistNode]) == 2
        assert [cast(OutputNode, n) for n in resolved if type(n) == OutputNode][0].playlist_name() == "out_pl_name"

    def test_resolve_node_list_dynamic_template(self):
        playlists = [testutil.create_empty_playlist_dict(f"BAR-{i}") for i in range(0, 3)]
        mock_client = MockClient([], playlists)
        input_nodes = [
            (
                "template",
                {
                    "type": "dynamic_template",
                    "template": {
                        "{varA} foo": {"type": "playlist", "uri": "{varB}"},
                        "{varA} bar": {"type": "output", "input": "{varA} foo", "playlist_name": "{varA} - {varB}"},
                    },
                    "instances": [{"varA": "FOO-1", "varB": "BAR-1"}, {"varA": "FOO-2", "varB": "BAR-2"}],
                },
            )
        ]
        sp_client = self.get_nocache_client(mock_client)
        resolved_list = nodes.resolve_node_list(sp_client, input_nodes)
        assert len(resolved_list) == 4

        resolved = {node.nid: node for node in resolved_list}
        for i in [1, 2]:
            assert resolved[f"FOO-{i} foo"] == PlaylistNode(
                spotify_client=sp_client, node_id=f"FOO-{i} foo", uri=f"BAR-{i}"
            )
            assert resolved[f"FOO-{i} bar"] == OutputNode(
                spotify_client=sp_client,
                node_id=f"FOO-{i} bar",
                input=f"FOO-{i} foo",
                playlist_name=f"FOO-{i} - BAR-{i}",
            )
