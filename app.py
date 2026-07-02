import os
import random
import itertools
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy.exc import IntegrityError

from models import db, Artist, Song, User, Swipe

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')

database_url = os.environ.get('DATABASE_URL', '')
if database_url.startswith('postgres://'):
    # SQLAlchemy requires the postgresql:// scheme; Render's DATABASE_URL uses postgres://
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

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

def _fetch_track(genre, exclude_ids=None):
    """Pull up to 20 recent tracks for a genre and return one at random, skipping exclude_ids."""
    exclude_ids = exclude_ids or set()
    sc = _get_sc()
    candidates = []
    for track in itertools.islice(sc.get_tag_tracks_recent(genre), 20):
        if str(track.id) in exclude_ids:
            continue
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
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'status': 'error', 'message': 'not logged in'}), 401


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'status': 'error', 'message': 'username, email, and password required'}), 400

    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        onboarding_genres=data.get('onboarding_genres'),
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'username or email already taken'}), 409

    login_user(user)
    return jsonify({'status': 'ok', 'message': 'registered', 'user': user.username})


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'status': 'error', 'message': 'username and password required'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'status': 'error', 'message': 'invalid username or password'}), 401

    login_user(user)
    return jsonify({'status': 'ok', 'message': 'logged in', 'user': user.username})


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


def _get_or_create_song(soundcloud_id):
    """Look up a song by SoundCloud id, fetching from SoundCloud and inserting
    (song + artist, if needed) when it isn't in the DB yet."""
    song = Song.query.filter_by(soundcloud_id=str(soundcloud_id)).first()
    if song:
        return song

    sc = _get_sc()
    track = sc.get_track(int(soundcloud_id))
    if not track:
        return None

    artist = Artist.query.filter_by(name=track.user.username).first()
    if not artist:
        artist = Artist(name=track.user.username, country=track.user.country_code)
        db.session.add(artist)
        db.session.flush()

    song = Song(
        soundcloud_id=str(track.id),
        title=track.title,
        artist_id=artist.artist_id,
        genre=track.genre,
        duration=track.duration,
    )
    db.session.add(song)
    db.session.flush()
    return song


@app.route('/swipe', methods=['POST'])
@login_required
def log_swipe():
    data = request.get_json()
    song_id = data.get('song_id') if data else None
    direction = data.get('direction') if data else None
    if not song_id or direction not in ('like', 'dislike'):
        return jsonify({'status': 'error', 'message': 'song_id and direction (like/dislike) required'}), 400

    try:
        song = _get_or_create_song(song_id)
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'SoundCloud error: {str(e)}'}), 502

    if not song:
        return jsonify({'status': 'error', 'message': 'song not found on SoundCloud'}), 404

    swipe = Swipe(user_id=current_user.user_id, song_id=song.song_id, like=(direction == 'like'))
    current_user.latest_swipe_song_id = song.song_id
    db.session.add(swipe)
    db.session.commit()

    return jsonify({'status': 'ok', 'song_id': song_id, 'direction': direction})


@app.route('/recommend', methods=['GET'])
@login_required
def recommend():
    # TODO: send liked/disliked tracks to Gemini and use its returned genre/query
    # to call sc.search_tracks() or _fetch_track(). For now, swipe history is only
    # used to avoid re-recommending songs the user already swiped on.
    already_swiped = {
        song.soundcloud_id
        for song in Song.query.join(Swipe).filter(Swipe.user_id == current_user.user_id)
    }

    genre = random.choice(GENRES)
    try:
        track = _fetch_track(genre, exclude_ids=already_swiped)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'SoundCloud error: {str(e)}'}), 502
    if not track:
        return jsonify({'status': 'error', 'message': 'no new tracks found'}), 404
    return jsonify({'status': 'ok', 'song': _track_to_dict(track)})


if __name__ == '__main__':
    app.run(debug=True)
