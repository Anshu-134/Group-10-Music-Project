"""
 * Retrieves candidate tracks for a genre, falling back to mock data if the API isn't configured or unavailable
 * Uses SoundCloud API v2, so response fields may change over time. 
"""
import os
import requests
 
from src.data.mock_songs import by_genre as mock_songs_by_genre
 
DEFAULT_LIMIT = 20
 
 
def _track_from_api(raw):
    return {
        'id': raw.get('id'),
        'title': raw.get('title'),
        'artist': (raw.get('user') or {}).get('username'),
        'genre': raw.get('genre'),
        'duration_ms': raw.get('duration'),
        'permalink_url': raw.get('permalink_url'),
        'artwork_url': raw.get('artwork_url'),
        'streamable': raw.get('streamable'),
        'policy': raw.get('policy'),
    }

def get_tracks_by_genre(genre, limit=DEFAULT_LIMIT):
    client_id = os.environ.get('SOUNDCLOUD_CLIENT_ID')
 
    if not client_id:
        print('[soundcloud_service] SOUNDCLOUD_CLIENT_ID not set -- using mock songs')
        return mock_songs_by_genre(genre)
 
    try:
        resp = requests.get(
            'https://api-v2.soundcloud.com/search/tracks',
            params={'q': genre, 'client_id': client_id, 'limit': limit},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        tracks = [_track_from_api(t) for t in data.get('collection', [])]
        return tracks if tracks else mock_songs_by_genre(genre)
    except Exception as e:
        print(f'[soundcloud_service] SoundCloud request failed ({e}) -- falling back to mock songs')
        return mock_songs_by_genre(genre)