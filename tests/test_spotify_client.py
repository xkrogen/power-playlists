from dynamicplaylist import utils
from dynamicplaylist.spotify_client import *
from test_mocks import MockClient


class TestSpotifyClient:

    def test_playlist_cache_via_client(self, tmp_path):
        mock_client = MockClient('t1,t2')
        app_config = utils.AppConfig()
        app_config.cache_dir = f'{tmp_path}/cache'
        client = SpotifyClient(app_config, mock_client)
        client.current_user_playlists()

        pl_from_client = client.playlist('test_pl_uri')
        pl_via_cache = client.playlist('test_pl_uri')
        assert pl_via_cache == pl_from_client
        assert mock_client.api_call_counts['playlist'] == 1

        pl_via_cache_2 = client.playlist('test_pl_uri')
        assert pl_via_cache_2 == pl_via_cache
        assert mock_client.api_call_counts['playlist'] == 1

        pl_forced = client.playlist('test_pl_uri', force_reload=True)
        assert pl_forced == pl_via_cache
        assert mock_client.api_call_counts['playlist'] == 2

    def test_playlist_cache_direct(self, tmp_path):
        mock_client = MockClient('t1,t2')
        app_config = utils.AppConfig()
        app_config.cache_dir = f'{tmp_path}/cache'
        playlist_cache = PlaylistCache(app_config, lambda uri: mock_client.playlist(uri))
        pl_from_client = mock_client.playlist('test_pl_uri')
        pl_via_cache, cached = playlist_cache.get_playlist('test_pl_uri')
        assert pl_via_cache == pl_from_client
        assert not cached
        assert mock_client.api_call_counts['playlist'] == 2
        assert os.path.exists(f'{playlist_cache.playlist_cache_dir}/test_pl_uri')

        pl_via_cache_2, cached = playlist_cache.get_playlist('test_pl_uri')
        assert pl_via_cache_2 == pl_via_cache
        assert cached
        assert mock_client.api_call_counts['playlist'] == 2

        pl_forced, cached = playlist_cache.get_playlist('test_pl_uri', force_reload=True)
        assert pl_forced == pl_via_cache
        assert not cached
        assert mock_client.api_call_counts['playlist'] == 3
