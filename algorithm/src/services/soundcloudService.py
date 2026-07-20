"""
 * Retrieves candidate tracks for a genre, falling back to mock data if the API isn't configured or unavailable
 * Uses SoundCloud API v2, so response fields may change over time. 
"""
import os
import re
import requests
from soundcloud import SoundCloud
 
from src.data.mockSongs import by_genre as mock_songs_by_genre
 
DEFAULT_LIMIT = 20
 
_client_id = None
 
def _get_client_id():
    global _client_id
    if _client_id is None:
        _client_id = os.environ.get('SOUNDCLOUD_CLIENT_ID') or SoundCloud.generate_client_id()
    return _client_id
 
 
def _redact(text):
    """SoundCloud error strings embed the full request URL, client_id
    included -- strip it out before this ever hits a log."""
    return re.sub(r'client_id=[^&\s]+', 'client_id=***', str(text))
 
 
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
    client_id = _get_client_id()
 
    try:
        resp = requests.get(
            'https://api-v2.soundcloud.com/search/tracks',
            params={'q': genre, 'client_id': client_id, 'limit': limit},
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                               '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Referer': 'https://soundcloud.com/',
                'Origin': 'https://soundcloud.com',
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        tracks = [_track_from_api(t) for t in data.get('collection', [])]
        return tracks if tracks else mock_songs_by_genre(genre)
    except Exception as e:
        print(f'[soundcloud_service] SoundCloud request failed ({_redact(e)}) -- falling back to mock songs')
        return mock_songs_by_genre(genre)