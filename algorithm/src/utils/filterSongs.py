"""
 * Filters candidate tracks to those that are playable and have not
 * already been swiped on. Works with both SoundCloud API results and mock
 * data, since both share the same track format. 
"""

def filter_songs(candidates, exclude_ids=None):
    """
    @param candidates: list of dicts with at least id/streamable/policy/artwork_url
    @param exclude_ids: ids the user has already swiped on
    @return: filtered list of candidates
    """
    exclude_ids = exclude_ids or []
    excluded = {str(x) for x in exclude_ids}
 
    def keep(track):
        if not track:
            return False
        if str(track.get('id')) in excluded:
            return False
        if track.get('streamable') is False:
            return False
        if track.get('policy') == 'BLOCK':
            return False
        if not track.get('artwork_url'):
            return False
        return True
 
    return [track for track in candidates if keep(track)]