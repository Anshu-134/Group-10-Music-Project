"""
 * 1. Tries Gemini for genre selection
 * 2. Falls back to band
 * 3. Fetches candidate tracks from SoundCloud
 * 4. Filters out unplayable tracks
 * 5. Weighted-pick among remaining candidates, favoring liked artists

One function recommendationRoutes.js calls.
"""

from src.utils import score_songs
from src.utils.filter_songs import filter_songs
from src.services import soundcloud_service
from src.services import gemini_service
from src.data.mock_user import SWIPE_HISTORY as MOCK_SWIPE_HISTORY

def get_recommendation(genres=None, exclude_ids=None, swipe_history=None, preferred_genres=None):
    genres = genres or []
    exclude_ids = exclude_ids or []
    preferred_genres = preferred_genres or []
 
    if not isinstance(genres, list) or len(genres) == 0:
        return {'status': 'error', 'message': 'genres array is required'}
    history = swipe_history if (isinstance(swipe_history, list) and len(swipe_history) > 0) else MOCK_SWIPE_HISTORY
 
    genre = None
    used_gemini = False
 
    if gemini_service.is_enabled():
        try:
            suggestion = gemini_service.suggest_genre(history, genres)
            if suggestion:
                genre = suggestion
                used_gemini = True
        except Exception as e:
            print(f'[recommendation_service] Gemini suggestion failed, falling back to bandit: {e}')
 
    if not genre:
        genre = score_songs.pick_genre(history, genres, preferred_genres)
 
    raw_candidates = soundcloud_service.get_tracks_by_genre(genre)
    candidates = filter_songs(raw_candidates, exclude_ids)
 
    if not candidates:
        return {'status': 'error', 'message': f'no candidates found for genre: {genre}'}
 
    song = score_songs.choose_track(candidates, history)
    score = score_songs.confidence_score(genre, song, history)
 
    return {'status': 'ok', 'song': song, 'chosenGenre': genre, 'usedGemini': used_gemini, 'score': score}