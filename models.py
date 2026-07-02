import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Artist(db.Model):
    __tablename__ = 'artists'

    artist_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    country = db.Column(db.Text)

    songs = db.relationship('Song', backref='artist')


class Song(db.Model):
    __tablename__ = 'songs'

    song_id = db.Column(db.Integer, primary_key=True)
    soundcloud_id = db.Column(db.Text, nullable=False, unique=True)
    title = db.Column(db.Text, nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.artist_id'))
    genre = db.Column(db.Text)
    duration = db.Column(db.Integer)
    album = db.Column(db.Text)
    year = db.Column(db.Integer)

    swipes = db.relationship('Swipe', backref='song')


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, nullable=False, unique=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    onboarding_genres = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    latest_swipe_song_id = db.Column(db.Integer, db.ForeignKey('songs.song_id'))

    def get_id(self):
        # flask-login expects the id column to be named `id`; ours is `user_id`.
        return str(self.user_id)


class Swipe(db.Model):
    __tablename__ = 'swipes'

    swipe_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.song_id'), nullable=False)
    like = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)


class Recommendation(db.Model):
    __tablename__ = 'recommendations'

    # schema.sql defines no primary key for this table; user_id+song_id is the
    # natural composite key, so it's used here for ORM mapping.
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.song_id'), primary_key=True)
    score = db.Column(db.Float, nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
