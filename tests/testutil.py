def create_track_dict(uri):
    return {
        'track': {
            'uri': uri
        }
    }


def uris_from_tracks(tracks):
    return [track['track']['uri'] for track in tracks]


def assert_playlist_uris(mock_client, playlist_uri, track_uri_list):
    assert uris_from_tracks(mock_client._get_playlist(playlist_uri)['tracks']['items']) == track_uri_list
