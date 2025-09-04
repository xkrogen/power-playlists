import os

from test_mocks import MockClient

from powerplaylists.spotify_client import PlaylistCache, SpotifyClient, utils


class TestSpotifyClient:
    def test_playlist_cache_via_client(self, tmp_path):
        mock_client = MockClient("t1,t2")
        app_config = utils.AppConfig()
        app_config.cache_dir = f"{tmp_path}/cache"
        client = SpotifyClient(app_config, mock_client)
        client.current_user_playlists()

        pl_from_client = client.playlist("test_pl_uri")
        pl_via_cache = client.playlist("test_pl_uri")
        assert pl_via_cache == pl_from_client
        assert mock_client.api_call_counts["playlist"] == 1

        pl_via_cache_2 = client.playlist("test_pl_uri")
        assert pl_via_cache_2 == pl_via_cache
        assert mock_client.api_call_counts["playlist"] == 1

        pl_forced = client.playlist("test_pl_uri", force_reload=True)
        assert pl_forced == pl_via_cache
        assert mock_client.api_call_counts["playlist"] == 2

    def test_playlist_cache_direct(self, tmp_path):
        mock_client = MockClient("t1,t2")
        app_config = utils.AppConfig()
        app_config.cache_dir = f"{tmp_path}/cache"
        playlist_cache = PlaylistCache(app_config, lambda uri: mock_client.playlist(uri))
        pl_from_client = mock_client.playlist("test_pl_uri")
        pl_via_cache, cached = playlist_cache.get_playlist("test_pl_uri")
        assert pl_via_cache == pl_from_client
        assert not cached
        assert mock_client.api_call_counts["playlist"] == 2
        assert os.path.exists(f"{playlist_cache.playlist_cache_dir}/test_pl_uri")

        pl_via_cache_2, cached = playlist_cache.get_playlist("test_pl_uri")
        assert pl_via_cache_2 == pl_via_cache
        assert cached
        assert mock_client.api_call_counts["playlist"] == 2

        pl_forced, cached = playlist_cache.get_playlist("test_pl_uri", force_reload=True)
        assert pl_forced == pl_via_cache
        assert not cached
        assert mock_client.api_call_counts["playlist"] == 3

    def test_playlist_remove_empty_list(self, tmp_path):
        """Test that removing an empty list of tracks doesn't call the Spotify API."""
        mock_client = MockClient("t1,t2,t3")
        app_config = utils.AppConfig()
        app_config.cache_dir = f"{tmp_path}/cache"
        client = SpotifyClient(app_config, mock_client)
        client.current_user_playlists()

        # Get initial API call count
        initial_remove_calls = mock_client.api_call_counts.get("playlist_remove_specific_occurrences_of_items", 0)
        initial_playlist_calls = mock_client.api_call_counts.get("playlist", 0)

        # Call with empty removal list and no snapshot_id - should fetch playlist for snapshot_id
        result = client.playlist_remove_specific_occurrences_of_items("test_pl_uri", [])

        # Should return a snapshot_id without calling the remove API
        assert result == "ignored"  # MockClient returns "ignored" as snapshot_id
        assert (
            mock_client.api_call_counts.get("playlist_remove_specific_occurrences_of_items", 0) == initial_remove_calls
        )
        assert mock_client.api_call_counts.get("playlist", 0) == initial_playlist_calls + 1

        # Call with empty removal list but with snapshot_id provided - should not fetch playlist
        result2 = client.playlist_remove_specific_occurrences_of_items("test_pl_uri", [], snapshot_id="test_snapshot")

        # Should return the provided snapshot_id without any API calls
        assert result2 == "test_snapshot"
        assert (
            mock_client.api_call_counts.get("playlist_remove_specific_occurrences_of_items", 0) == initial_remove_calls
        )
        assert (
            mock_client.api_call_counts.get("playlist", 0) == initial_playlist_calls + 1
        )  # No additional playlist calls
