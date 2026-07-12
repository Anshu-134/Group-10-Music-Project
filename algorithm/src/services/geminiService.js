/**
 * Optional AI service for genre selection. Gemini uses user's swipe history to suggest a genre.
 * If failure, recommendations fall back into standard bandit algorithm. 
 * 
 * Note: I still need to verify the gemini model. 
 */

const DEFAULT_MODEL = process.env.GEMINI_MODEL || 'gemini-2.0-flash';
 
function isEnabled() {
  return Boolean(process.env.GEMINI_API_KEY);
}
 
function buildPrompt(swipeHistory, availableGenres) {
  const liked = swipeHistory
    .filter((s) => s.liked)
    .map((s) => `${s.artist || 'an unknown artist'} (${s.genre})`);
  const disliked = swipeHistory
    .filter((s) => !s.liked)
    .map((s) => `${s.artist || 'an unknown artist'} (${s.genre})`);
 
  return [
    'You are picking exactly ONE genre for a Tinder-style music discovery app to show the user next.',
    `Allowed genres: ${availableGenres.join(', ')}.`,
    liked.length ? `The listener liked: ${liked.join(', ')}.` : 'The listener has not liked anything yet.',
    disliked.length ? `The listener disliked: ${disliked.join(', ')}.` : '',
    'Reply with exactly one genre from the allowed list, lowercase, and nothing else — no punctuation, no explanation.',
  ].filter(Boolean).join('\n');
}
 
/**
 * @returns {Promise<string|null>} will return null if Gemini is not enabled
 */
async function suggestGenre(swipeHistory, availableGenres) {
  if (!isEnabled() || !swipeHistory.length) return null;
 
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${DEFAULT_MODEL}:generateContent?key=${process.env.GEMINI_API_KEY}`;
  const prompt = buildPrompt(swipeHistory, availableGenres);
 
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.4, maxOutputTokens: 20 },
    }),
  });
 
  if (!res.ok) {
    throw new Error(`Gemini responded with status ${res.status}`);
  }
 
  const data = await res.json();
  const text = data?.candidates?.[0]?.content?.parts?.[0]?.text?.trim().toLowerCase();
  return availableGenres.includes(text) ? text : null;
}
 
module.exports = { isEnabled, suggestGenre };