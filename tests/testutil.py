def create_track_dict(uri):
    artists = [get_user_dict(f'artist_for_{uri}')]
    return {
        'track': {
            'id': uri,
            'uri': uri,
            'name': 'Track Name',
            'popularity': 50,
            'artists': artists,
            'album': {
                'uri': 'some_album_uri',
                'id': 'some_album',
                'album_type': 'album',
                'artists': artists,
                'name': 'Some Album',
                'release_date': '2020-01-01'
            }
        },
        'is_local': False,
        'added_at': '2020-01-01T00:00:00Z',
        'added_by': {
            'uri': 'some_user_uri',
            'id': 'some_user',
            'display_name': 'Some User'
        }
    }


def create_playlist_dict(uri, track_dicts, name=None):
    return {
        'name': name if name is not None else f'Track {uri}',
        'uri': uri,
        'id': uri,
        'tracks': {
            'total': len(track_dicts),
            'items': track_dicts
        },
        'public': False,
        'description': f'description for {uri}',
        'snapshot_id': 'ignored',
        'collaborative': False,
        'owner': get_user_dict(f'owner_of_{uri}'),
        'followers': get_followers_dict(5)
    }


def create_empty_playlist_dict(uri):
    return create_playlist_dict(uri, list())


def get_user_dict(uri):
    return {
        'uri': uri,
        'id': uri,
        'name': f'Test Artist {uri}',  # Artist uses 'name'
        'display_name': f'Test Playlist Owner for {uri}'  # owner uses display_name
    }


def get_followers_dict(cnt):
    return {'total': cnt}


def uris_from_tracks(tracks):
    return [track['track']['uri'] for track in tracks]


def assert_playlist_uris(mock_client, playlist_uri, track_uri_list):
    assert uris_from_tracks(mock_client._get_playlist(playlist_uri)['tracks']['items']) == track_uri_list
