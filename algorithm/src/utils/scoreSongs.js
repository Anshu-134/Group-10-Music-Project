/** 
 * This file converts swipe history into personalized music recommendations.
 * Epsilon-greedy multi-armed bandit: learns genre and artist preferences from likes/dislikes
 * Recommends what user is likely to already enjoy, but still explores new genres
 * New users: seeds recommendations using onboarding preferences to solve cold-start problem 
*/


/** Tunable parameters */
const SMOOTHING = 2.0;              // Laplace smoothing "phantom" swipes
const GENRE_TEMPERATURE = 0.6;      // lower = leans harder into favorites
const TRACK_TEMPERATURE = 0.8;
const EPSILON = 0.15;               // fraction of picks that explore randomly
const ARTIST_LIKE_WEIGHT = 3.0;     // how hard "liked this artist before" pulls
const MIN_SWIPES_FOR_PERSONALIZATION = 4; // cold-start threshold
const PREFERRED_GENRE_BIAS = 0.7;   // cold-start: chance we pick from preferredGenres at all
 
function affinityFrom(history, keyFn) {
  const likes = new Map();
  const dislikes = new Map();
 
  for (const swipe of history) {
    const key = keyFn(swipe);
    if (!key) continue;
    const bucket = swipe.liked ? likes : dislikes;
    bucket.set(key, (bucket.get(key) || 0) + 1);
  }
 
  const keys = new Set([...likes.keys(), ...dislikes.keys()]);
  const scores = {};
  for (const key of keys) {
    const l = likes.get(key) || 0;
    const d = dislikes.get(key) || 0;
    scores[key] = (l - d) / (l + d + SMOOTHING);
  }
  return scores;
}
 
/** { genre: score in [-1, 1] }. Positive = user tends to like it. Negative = user tends to dislike*/
function genreAffinity(history) {
  return affinityFrom(history, (s) => s.genre);
}
 
/** { artistName: score in [-1, 1] }. Same idea as genreAffinity */
function artistAffinity(history) {
  return affinityFrom(history, (s) => s.artist);
}
 
/** Weighted-random pick over `items` using softmax(weightFn(item)). */
function softmaxChoice(items, weightFn, temperature) {
  if (!items.length) return null;
  const scaled = items.map((item) => weightFn(item) / temperature);
  const top = Math.max(...scaled);
  const exps = scaled.map((s) => Math.exp(s - top)); 
  const total = exps.reduce((a, b) => a + b, 0);
  const weights = exps.map((e) => e / total);
 
  let r = Math.random();
  for (let i = 0; i < items.length; i++) {
    r -= weights[i];
    if (r <= 0) return items[i];
  }
  return items[items.length - 1];
}
 
/**
 * Epsilon-greedy genre strategy: recommends genres the user is likely to enjoy, 
 * but explores random genres occasionally. Onboarding preferences will guide for new 
 * users until enough swipe history is available. 
 */
function pickGenre(history, genres, preferredGenres = []) {
  const totalSwipes = history.length;
  const validPreferred = preferredGenres.filter((g) => genres.includes(g));
 
  if (totalSwipes < MIN_SWIPES_FOR_PERSONALIZATION) {
    if (validPreferred.length && Math.random() < PREFERRED_GENRE_BIAS) {
      return validPreferred[Math.floor(Math.random() * validPreferred.length)];
    }
    return genres[Math.floor(Math.random() * genres.length)];
  }
 
  if (Math.random() < EPSILON) {
    return genres[Math.floor(Math.random() * genres.length)];
  }
 
  const scores = genreAffinity(history);
  return softmaxChoice(genres, (g) => scores[g] || 0, GENRE_TEMPERATURE);
}
 
/**
 * Weighted pick among candidate tracks (already fetched for the chosen
 * genre), favoring artists this user has liked before. Candidate tracks
 * are expected to have a `.artist` field (artist display name).
 */
function chooseTrack(candidates, history) {
  if (!candidates.length) return null;
  const scores = artistAffinity(history);
  return softmaxChoice(
    candidates,
    (track) => (scores[track.artist] || 0) * ARTIST_LIKE_WEIGHT,
    TRACK_TEMPERATURE
  );
}
 
/** Best-liked genre for this user, or null if there's not enough info yet. */
function topGenre(history) {
  const scores = genreAffinity(history);
  const positive = Object.entries(scores).filter(([, s]) => s > 0);
  if (!positive.length) return null;
  return positive.reduce((best, cur) => (cur[1] > best[1] ? cur : best))[0];
}
 
/**
 * Estimates confidence in a recommendation based on user data. Intended for analytics.
 * Note: not required for generating recs.
 */
function confidenceScore(chosenGenre, chosenTrack, history) {
  const genreScore = genreAffinity(history)[chosenGenre] || 0;
  const artistScore = chosenTrack ? (artistAffinity(history)[chosenTrack.artist] || 0) : 0;
  return genreScore + artistScore;
}
 
module.exports = {
  genreAffinity,
  artistAffinity,
  pickGenre,
  chooseTrack,
  topGenre,
  confidenceScore,
  SMOOTHING,
  GENRE_TEMPERATURE,
  TRACK_TEMPERATURE,
  EPSILON,
  ARTIST_LIKE_WEIGHT,
  MIN_SWIPES_FOR_PERSONALIZATION,
  PREFERRED_GENRE_BIAS,
};