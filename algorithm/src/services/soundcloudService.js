/**
 * Retrieves candidate tracks for a genre, falling back to mock data if the API isn't configured or unavailable
 * Uses SoundCloud API v2, so response fields may change over time. 
 */

const { byGenre: mockSongsByGenre } = require('../data/mockSongs');
 
const DEFAULT_LIMIT = 20;
 
/**
 * Maps raw SoundCloud API response to the application's track format
 * @param {object} raw - raw track from SoundCloud API
 * @returns {object} normalized track object
 */
function trackFromApi(raw) {
  return {
    id: raw.id,
    title: raw.title,
    artist: raw.user && raw.user.username,
    genre: raw.genre,
    duration_ms: raw.duration,
    permalink_url: raw.permalink_url,
    artwork_url: raw.artwork_url,
    streamable: raw.streamable,
    policy: raw.policy,
  };
}


/**
 * Fetches tracks matching genre. Returns mock data to continue operations if Soundcloud client ID is unavailable
 * @param {string} genre - The genre to search for
 * @param {object} [options] 
 * @param {number} [options.limit=20] - Max number of tracks to return
 * @returns {Promise<Array<object>>} List of tracks matching the genre
 */
async function getTracksByGenre(genre, { limit = DEFAULT_LIMIT } = {}) {
  const clientId = process.env.SOUNDCLOUD_CLIENT_ID;
 
  if (!clientId) {
    console.warn('[soundcloudService] SOUNDCLOUD_CLIENT_ID not set — using mock songs');
    return mockSongsByGenre(genre);
  }
 
  const url = new URL('https://api-v2.soundcloud.com/search/tracks');
  url.searchParams.set('q', genre);
  url.searchParams.set('client_id', clientId);
  url.searchParams.set('limit', String(limit));
 
  try {
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`SoundCloud responded with status ${res.status}`);
    }
    const data = await res.json();
    const tracks = (data.collection || []).map(trackFromApi);
    return tracks.length ? tracks : mockSongsByGenre(genre);
  } catch (err) {
    console.warn(`[soundcloudService] SoundCloud request failed (${err.message}) — falling back to mock songs`);
    return mockSongsByGenre(genre);
  }
}
 
module.exports = { getTracksByGenre };