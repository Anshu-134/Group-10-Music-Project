import os
import random
import itertools
from flask import Flask, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')

login_manager = LoginManager(app)

# --- SoundCloud ---
_sc = None

GENRES = [
    'electronic', 'hip-hop', 'indie', 'ambient', 'jazz',
    'rock', 'classical', 'pop', 'soul', 'metal', 'folk',
]

def _get_sc():
    global _sc
    if _sc is None:
        from soundcloud import SoundCloud
        client_id = os.environ.get('SOUNDCLOUD_CLIENT_ID') or SoundCloud.generate_client_id()
        _sc = SoundCloud(
            client_id=client_id,
            auth_token=os.environ.get('SOUNDCLOUD_AUTH_TOKEN') or None,
        )
    return _sc

def _fetch_track(genre):
    """Pull up to 20 recent tracks for a genre and return one at random."""
    sc = _get_sc()
    candidates = []
    for track in itertools.islice(sc.get_tag_tracks_recent(genre), 20):
        if track.streamable and track.artwork_url and track.policy != 'BLOCK':
            candidates.append(track)
            if len(candidates) >= 5:
                break
    return random.choice(candidates) if candidates else None

def _track_to_dict(track):
    return {
        'id': track.id,
        'title': track.title,
        'artist': track.user.username,
        'permalink_url': track.permalink_url,
        'artwork_url': track.artwork_url,
        'genre': track.genre,
        'duration_ms': track.duration,
    }


# --- Auth ---
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'status': 'error', 'message': 'not logged in'}), 401


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username'):
        return jsonify({'status': 'error', 'message': 'username required'}), 400
    # TODO: validate against DB
    user = User(id=data['username'])
    login_user(user)
    return jsonify({'status': 'ok', 'message': 'logged in', 'user': user.id})


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'status': 'ok', 'message': 'logged out'})


@app.route('/song', methods=['GET'])
@login_required
def get_song():
    genre = random.choice(GENRES)
    try:
        track = _fetch_track(genre)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'SoundCloud error: {str(e)}'}), 502
    if not track:
        return jsonify({'status': 'error', 'message': f'no streamable tracks found for genre: {genre}'}), 404
    return jsonify({'status': 'ok', 'song': _track_to_dict(track)})


@app.route('/swipe', methods=['POST'])
@login_required
def log_swipe():
    data = request.get_json()
    song_id = data.get('song_id') if data else None
    direction = data.get('direction') if data else None
    if not song_id or direction not in ('like', 'dislike'):
        return jsonify({'status': 'error', 'message': 'song_id and direction (like/dislike) required'}), 400
    # TODO: write swipe record to DB
    return jsonify({'status': 'ok', 'song_id': song_id, 'direction': direction})


@app.route('/recommend', methods=['GET'])
@login_required
def recommend():
    # TODO: pull swipe history from DB, send liked/disliked tracks to Gemini,
    # use Gemini's returned genre/query to call sc.search_tracks() or _fetch_track()
    genre = random.choice(GENRES)
    try:
        track = _fetch_track(genre)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'SoundCloud error: {str(e)}'}), 502
    if not track:
        return jsonify({'status': 'error', 'message': 'no tracks found'}), 404
    return jsonify({'status': 'ok', 'song': _track_to_dict(track)})


if __name__ == '__main__':
    app.run(debug=True)
