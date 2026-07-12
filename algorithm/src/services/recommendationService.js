/**
 * 1. Tries Gemini for genre selection
 * 2. Falls back to band
 * 3. Fetches candidate tracks from SoundCloud
 * 4. Filters out unplayable tracks
 * 5. Weighted-pick among remaining candidates, favoring liked artists
 */


/**One function recommendationRoutes.js calls.  */
const scoreSongs = require('../utils/scoreSongs');
const filterSongs = require('../utils/filterSongs');
const soundcloudService = require('./soundcloudService');
const geminiService = require('./geminiService');
const { swipeHistory: mockSwipeHistory } = require('../data/mockUser');

async function getRecommendation({ genres, excludeIds = [], swipeHistory, preferredGenres = [] }) {
  if (!Array.isArray(genres) || genres.length === 0) {
    return { status: 'error', message: 'genres array is required' };
  }
 
  // No history supplied (e.g. manual testing against this service directly)
  // falls back to a fixture so the algorithm still has something to react to.
  const history = Array.isArray(swipeHistory) && swipeHistory.length
    ? swipeHistory
    : mockSwipeHistory;
 
  let genre = null;
  let usedGemini = false;
 
  if (geminiService.isEnabled()) {
    try {
      const suggestion = await geminiService.suggestGenre(history, genres);
      if (suggestion) {
        genre = suggestion;
        usedGemini = true;
      }
    } catch (err) {
      console.warn(`[recommendationService] Gemini suggestion failed, falling back to bandit: ${err.message}`);
    }
  }
 
  if (!genre) {
    genre = scoreSongs.pickGenre(history, genres, preferredGenres);
  }
 
  const rawCandidates = await soundcloudService.getTracksByGenre(genre);
  const candidates = filterSongs(rawCandidates, excludeIds);
 
  if (!candidates.length) {
    return { status: 'error', message: `no candidates found for genre: ${genre}` };
  }
 
  const song = scoreSongs.chooseTrack(candidates, history);
  const score = scoreSongs.confidenceScore(genre, song, history);
 
  return { status: 'ok', song, chosenGenre: genre, usedGemini, score };
}
 
module.exports = { getRecommendation };