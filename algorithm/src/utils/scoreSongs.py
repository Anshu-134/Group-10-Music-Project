"""
 * This file converts swipe history into personalized music recommendations.
 * Epsilon-greedy multi-armed bandit: learns genre and artist preferences from likes/dislikes
 * Recommends what user is likely to already enjoy, but still explores new genres
 * New users: seeds recommendations using onboarding preferences to solve cold-start problem 
"""

import math
import random

"""Parameters"""
SMOOTHING = 2.0                    
# Laplace smoothing "phantom" swipes
GENRE_TEMPERATURE = 0.6            
# lower = leans harder into favorites
TRACK_TEMPERATURE = 0.8
EPSILON = 0.15                     
# fraction of picks that explore randomly
ARTIST_LIKE_WEIGHT = 3.0           
# how hard "liked this artist before" pulls
MIN_SWIPES_FOR_PERSONALIZATION = 4 
# cold-start threshold
PREFERRED_GENRE_BIAS = 0.7 
#cold-start: chance we pick from preferredGenres at all
 
def _affinity_from(history, key_fn):
    likes = {}
    dislikes = {}
 
    for swipe in history:
        key = key_fn(swipe)
        if not key:
            continue
        bucket = likes if swipe.get('liked') else dislikes
        bucket[key] = bucket.get(key, 0) + 1
 
    keys = set(likes) | set(dislikes)
    scores = {}
    for key in keys:
        l = likes.get(key, 0)
        d = dislikes.get(key, 0)
        scores[key] = (l - d) / (l + d + SMOOTHING)
    return scores
 
 
def genre_affinity(history):
    """{genre: score in [-1, 1]}. Positive = user tends to like it."""
    return _affinity_from(history, lambda s: s.get('genre'))
 
 
def artist_affinity(history):
    """{artist_name: score in [-1, 1]}."""
    return _affinity_from(history, lambda s: s.get('artist'))
 
 
def _softmax_choice(items, weight_fn, temperature):
    """Weighted-random pick over `items` using softmax(weight_fn(item))."""
    if not items:
        return None
    scaled = [weight_fn(item) / temperature for item in items]
    top = max(scaled)
    exps = [math.exp(s - top) for s in scaled]  # subtract max for stability
    total = sum(exps)
    weights = [e / total for e in exps]
 
    r = random.random()
    for item, w in zip(items, weights):
        r -= w
        if r <= 0:
            return item
    return items[-1]  # floating point fallback
 
 
def pick_genre(history, genres, preferred_genres=None):
    """
    Epsilon-greedy genre pick
    """
    preferred_genres = preferred_genres or []
    total_swipes = len(history)
    valid_preferred = [g for g in preferred_genres if g in genres]
 
    if total_swipes < MIN_SWIPES_FOR_PERSONALIZATION:
        if valid_preferred and random.random() < PREFERRED_GENRE_BIAS:
            return random.choice(valid_preferred)
        return random.choice(genres)
 
    if random.random() < EPSILON:
        return random.choice(genres)
 
    scores = genre_affinity(history)
    return _softmax_choice(genres, lambda g: scores.get(g, 0.0), GENRE_TEMPERATURE)
 
 
def choose_track(candidates, history):
    """
    Weighted pick among candidate tracks (already fetched for the chosen
    genre), favoring artists this user has liked before. Candidate tracks
    are expected to have an "artist" key (artist display name).
    """
    if not candidates:
        return None
    scores = artist_affinity(history)
    return _softmax_choice(
        candidates,
        lambda track: scores.get(track.get('artist'), 0.0) * ARTIST_LIKE_WEIGHT,
        TRACK_TEMPERATURE,
    )
 
def top_genre(history):
    """Best-liked genre for this user, or None if there's no positive signal yet."""
    scores = genre_affinity(history)
    positive = {g: s for g, s in scores.items() if s > 0}
    if not positive:
        return None
    return max(positive, key=positive.get)
 
 
def confidence_score(chosen_genre, chosen_track, history):
    """
    A rough "how confident is this pick" number, for callers that want to
    persist it (e.g. the `recommendations` table already defined in
    schema.sql/models.py, currently unused). Not required for /recommend to
    work -- purely informational.
    """
    genre_score = genre_affinity(history).get(chosen_genre, 0.0)
    artist_score = 0.0
    if chosen_track:
        artist_score = artist_affinity(history).get(chosen_track.get('artist'), 0.0)
    return genre_score + artist_score