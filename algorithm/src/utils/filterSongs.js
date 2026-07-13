/** 
 * Filters candidate tracks to those that are playable and have not
 * already been swiped on. Works with both SoundCloud API results and mock
 * data, since both share the same track format. 
 * 
 * @param {Array<object>} candidates - Candidate tracks
 * @param {Array<string|number>} excludeIds - IDS of previously swiped tracks
 * @returns {Array<object>} Filtered list of playable tracks
 */


function filterSongs(candidates, excludeIds = []) {
  const excluded = new Set(excludeIds.map(String));
 
  return candidates.filter((track) => {
    if (!track) return false;
    if (excluded.has(String(track.id))) return false;
    if (track.streamable === false) return false;
    if (track.policy === 'BLOCK') return false;
    if (!track.artwork_url) return false;
    return true;
  });
}
 
module.exports = filterSongs;