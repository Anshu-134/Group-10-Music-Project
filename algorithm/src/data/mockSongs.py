MOCK_SONGS = [
        {
        "id": 900000001,
        "title": "Blinding Lights",
        "artist": "The Weeknd",
        "genre": "pop",
        "duration_ms": 200000,
        "permalink_url": "https://soundcloud.com/mock/blinding-lights",
        "artwork_url": "https://picsum.photos/seed/900000001/300",
        "streamable": True,
        "policy": "ALLOW",
    },
    {
        "id": 900000002,
        "title": "Cruel Summer",
        "artist": "Taylor Swift",
        "genre": "pop",
        "duration_ms": 178000,
        "permalink_url": "https://soundcloud.com/mock/cruel-summer",
        "artwork_url": "https://picsum.photos/seed/900000002/300",
        "streamable": True,
        "policy": "ALLOW",
    },

    # Hip-Hop
    {
        "id": 900000003,
        "title": "HUMBLE.",
        "artist": "Kendrick Lamar",
        "genre": "hip-hop",
        "duration_ms": 177000,
        "permalink_url": "https://soundcloud.com/mock/humble",
        "artwork_url": "https://picsum.photos/seed/900000003/300",
        "streamable": True,
        "policy": "ALLOW",
    },
    {
        "id": 900000004,
        "title": "God's Plan",
        "artist": "Drake",
        "genre": "hip-hop",
        "duration_ms": 198000,
        "permalink_url": "https://soundcloud.com/mock/gods-plan",
        "artwork_url": "https://picsum.photos/seed/900000004/300",
        "streamable": True,
        "policy": "ALLOW",
    },

    # Indie
    {
        "id": 900000005,
        "title": "The Less I Know The Better",
        "artist": "Tame Impala",
        "genre": "indie",
        "duration_ms": 216000,
        "permalink_url": "https://soundcloud.com/mock/the-less-i-know-the-better",
        "artwork_url": "https://picsum.photos/seed/900000005/300",
        "streamable": True,
        "policy": "ALLOW",
    },
    {
        "id": 900000006,
        "title": "Sweater Weather",
        "artist": "The Neighbourhood",
        "genre": "indie",
        "duration_ms": 240000,
        "permalink_url": "https://soundcloud.com/mock/sweater-weather",
        "artwork_url": "https://picsum.photos/seed/900000006/300",
        "streamable": True,
        "policy": "ALLOW",
    },
]
 
 
def by_genre(genre):
    """All mock songs tagged with a given genre (used by soundcloud_service's fallback)."""
    return [song for song in MOCK_SONGS if song["genre"] == genre]