import os
import random
import itertools
import re
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
 
from sqlalchemy.exc import IntegrityError
 
from models import db, Artist, Song, User, Swipe
 
load_dotenv()
 
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')
 
# Frontend is on Vercel, backend on Render — different origins, so the
# login session cookie needs SameSite=None + Secure to survive the
# cross-site request, and CORS needs supports_credentials=True so the
# browser will actually send/accept it.
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
 
CORS(
    app,
    origins=['https://anshu-134.github.io'],
    supports_credentials=True,
)
 
database_url = os.environ.get('DATABASE_URL', '')
if database_url.startswith('postgres://'):
    # SQLAlchemy requires the postgresql:// scheme; Render's DATABASE_URL uses postgres://
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
 
db.init_app(app)
 
login_manager = LoginManager(app)
ALGORITHM_SERVICE_URL = os.environ.get('ALGORITHM_SERVICE_URL', 'http://localhost:4000')
ALGORITHM_SERVICE_TIMEOUT = 25

# --- SoundCloud ---
_sc = None
 
GENRES = [
    'electronic', 'hip-hop', 'indie', 'ambient', 'jazz',
    'rock', 'classical', 'pop', 'soul', 'metal', 'folk',
]
 
ONBOARDING_GENRE_MAP = {
    'indie': 'indie',
    'r&b': 'soul',
    'hip-hop': 'hip-hop',
    'pop': 'pop',
    'rock': 'rock',
    'edm': 'electronic',
    'classical': 'classical',
}
 
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
 
def _redact(text):
    """SoundCloud error strings embed the full request URL, client_id
    included -- never let that reach a log line or an API response."""
    return re.sub(r'client_id=[^&\s]+', 'client_id=***', str(text))
 
 
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
 
def _get_swipe_history(user_id):
    """[{genre, artist, liked}] for this user -- the training signal handed
    to the algorithm service (algorithm/src/utils/scoreSongs.py) on every
    /recommend call."""
    rows = (
        db.session.query(Song.genre, Artist.name, Swipe.like)
        .join(Swipe, Swipe.song_id == Song.song_id)
        .outerjoin(Artist, Song.artist_id == Artist.artist_id)
        .filter(Swipe.user_id == user_id)
        .all()
    )
    return [
        {'genre': genre, 'artist': artist_name, 'liked': bool(liked)}
        for genre, artist_name, liked in rows
    ]
 
def _get_preferred_genres(user):
    """Onboarding-survey genres, mapped to the canonical GENRES tags, for
    the algorithm service's cold-start seeding. Empty if the user skipped
    the survey or none of their answers map cleanly."""
    if not user.onboarding_genres:
        return []
    raw = [g.strip().lower() for g in user.onboarding_genres.split(',') if g.strip()]
    mapped = {ONBOARDING_GENRE_MAP[g] for g in raw if g in ONBOARDING_GENRE_MAP}
    return list(mapped)
 
 
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
 
 
@app.route('/survey', methods=['POST'])
@login_required
def survey():
    if current_user.fav_moods:
        return jsonify({'status': 'error', 'message': 'survey already submitted'}), 409
 
    data = request.get_json()
    genres = data.get('genres') if data else None
    mood = data.get('mood') if data else None
    if not genres or not mood:
        return jsonify({'status': 'error', 'message': 'genres and mood required'}), 400
 
    current_user.onboarding_genres = ','.join(genres) if isinstance(genres, list) else genres
    current_user.fav_moods = mood
    current_user.fav_artists = data.get('artists') or None
    db.session.commit()
 
    return jsonify({'status': 'ok', 'message': 'survey saved'})
 
 
@app.route('/song', methods=['GET'])
@login_required
def get_song():
    genre = random.choice(GENRES)
    try:
        track = _fetch_track(genre)
    except Exception as e:
        print(f'[app] SoundCloud error in /song: {_redact(e)}')
        return jsonify({'status': 'error', 'message': 'SoundCloud error, please try again'}), 502
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
        genre=track.genre or None,
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
        print(f'[app] SoundCloud error in /swipe: {_redact(e)}')
        return jsonify({'status': 'error', 'message': 'SoundCloud error, please try again'}), 502
 
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
    already_swiped = [
        song.soundcloud_id
        for song in Song.query.join(Swipe).filter(Swipe.user_id == current_user.user_id)
    ]
    swipe_history = _get_swipe_history(current_user.user_id)
    preferred_genres = _get_preferred_genres(current_user)
 
    try:
        resp = requests.post(
            f'{ALGORITHM_SERVICE_URL}/recommend',
            json={
                'genres': GENRES,
                'excludeIds': already_swiped,
                'swipeHistory': swipe_history,
                'preferredGenres': preferred_genres,
            },
            timeout=ALGORITHM_SERVICE_TIMEOUT,
        )
        data = resp.json()
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'algorithm service error: {str(e)}'}), 502
 
    if data.get('status') != 'ok':
        return jsonify(data), 404
 
    return jsonify({'status': 'ok', 'song': data['song']})
 
 
@app.route('/history', methods=['GET'])
@login_required
def history():
    swipes = (
        Swipe.query
        .filter_by(user_id=current_user.user_id)
        .order_by(Swipe.timestamp.desc())
        .limit(10)
        .all()
    )
    return jsonify({
        'status': 'ok',
        'history': [
            {
                'song_id': swipe.song.soundcloud_id,
                'title': swipe.song.title,
                'artist': swipe.song.artist.name,
                'direction': 'like' if swipe.like else 'dislike',
                'timestamp': swipe.timestamp.isoformat(),
            }
            for swipe in swipes
        ],
    })
 
 
@app.route('/profile', methods=['GET'])
@login_required
def profile():
    liked_count = Swipe.query.filter_by(user_id=current_user.user_id, like=True).count()
 
    top_genre = (
        db.session.query(Song.genre)
        .join(Swipe, Swipe.song_id == Song.song_id)
        .filter(Swipe.user_id == current_user.user_id, Swipe.like.is_(True), Song.genre.isnot(None), Song.genre != '')
        .group_by(Song.genre)
        .order_by(db.func.count(Swipe.swipe_id).desc())
        .first()
    )
    favorite_genre = top_genre[0] if top_genre else current_user.onboarding_genres
 
    return jsonify({
        'status': 'ok',
        'username': current_user.username,
        'liked_count': liked_count,
        'favorite_genre': favorite_genre,
        'joined_at': current_user.created_at.isoformat(),
    })
 
 
if __name__ == '__main__':
    app.run(debug=True)