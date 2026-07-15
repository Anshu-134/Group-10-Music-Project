from flask import Blueprint, request, jsonify
 
from src.services.recommendation_service import get_recommendation
from src.utils.score_songs import genre_affinity, artist_affinity, top_genre
 
recommend_bp = Blueprint('recommend_bp', __name__)
 
@recommend_bp.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.get_json(silent=True) or {}
        result = get_recommendation(
            genres=data.get('genres'),
            exclude_ids=data.get('excludeIds'),
            swipe_history=data.get('swipeHistory'),
            preferred_genres=data.get('preferredGenres'),
        )
        status_code = 200 if result.get('status') == 'ok' else 404
        return jsonify(result), status_code
    except Exception as e:
        print(f'[recommednation_routes] unexpected error: {e}')
        return jsonify({'status': 'error', 'message': 'internal server error'}), 500
 
 
# Pure scoring, no SoundCloud/mock fetch and no epsilon-greedy randomness --
# computes a favorite genre straight from Postgres), but kept available --
# e.g. for a richer "why am I seeing this" debug view later.
@recommend_bp.route('/affinity', methods=['POST'])
def affinity():
    try:
        data = request.get_json(silent=True) or {}
        history = data.get('swipeHistory')
        history = history if isinstance(history, list) else []
        return jsonify({
            'status': 'ok',
            'genreScores': genre_affinity(history),
            'artistScores': artist_affinity(history),
            'topGenre': top_genre(history),
        })
    except Exception as e:
        print(f'[recommednation_routes] /affinity error: {e}')
        return jsonify({'status': 'error', 'message': 'internal server error'}), 500
 
 
@recommend_bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})