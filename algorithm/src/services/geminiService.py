"""
 * Optional AI service for genre selection. Gemini uses user's swipe history to suggest a genre.
 * If failure, recommendations fall back into standard bandit algorithm. 
 * 
 * Note: I still need to verify the gemini model. 
"""
import os
import requests
 
DEFAULT_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
 
 
def is_enabled():
    return bool(os.environ.get('GEMINI_API_KEY'))
 
 
def _build_prompt(swipe_history, available_genres):
    liked = [
        f"{s.get('artist') or 'an unknown artist'} ({s.get('genre')})"
        for s in swipe_history if s.get('liked')
    ]
    disliked = [
        f"{s.get('artist') or 'an unknown artist'} ({s.get('genre')})"
        for s in swipe_history if not s.get('liked')
    ]
 
    lines = [
        'You are picking exactly ONE genre for a Tinder-style music discovery app to show the user next.',
        f"Allowed genres: {', '.join(available_genres)}.",
        f"The listener liked: {', '.join(liked)}." if liked else 'The listener has not liked anything yet.',
    ]
    if disliked:
        lines.append(f"The listener disliked: {', '.join(disliked)}.")
    lines.append(
        'Reply with exactly one genre from the allowed list, lowercase, and nothing else '
        '-- no punctuation, no explanation.'
    )
    return '\n'.join(lines)
 
 
def suggest_genre(swipe_history, available_genres):
    """
    @return: a genre string from available_genres, or None if Gemini isn't
        configured / didn't return a usable answer.
    """
    if not is_enabled() or not swipe_history:
        return None
 
    api_key = os.environ.get('GEMINI_API_KEY')
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{DEFAULT_MODEL}:generateContent'
    prompt = _build_prompt(swipe_history, available_genres)
 
    resp = requests.post(
        url,
        params={'key': api_key},
        json={
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': 0.4, 'maxOutputTokens': 20},
        },
        timeout=8,
    )
    resp.raise_for_status()
 
    data = resp.json()
    try:
        text = data['candidates'][0]['content']['parts'][0]['text'].strip().lower()
    except (KeyError, IndexError, TypeError):
        return None
 
    return text if text in available_genres else None