CREATE TABLE IF NOT EXISTS "artists" (
    "artist_id"	INTEGER PRIMARY KEY,
    "name"	TEXT NOT NULL,
    "country" TEXT
);

CREATE TABLE IF NOT EXISTS "songs" (
    "song_id"	INTEGER PRIMARY KEY,
    "soundcloud_id"	TEXT NOT NULL UNIQUE,
    "title"	TEXT NOT NULL,
    "artist_id"	INTEGER,
    "genre"	TEXT,
    "duration"	INTEGER,
    "album"	TEXT,
    "year"	INTEGER,
    FOREIGN KEY("artist_id") REFERENCES "artists"("artist_id")
);

CREATE TABLE IF NOT EXISTS "users" (
    "user_id" INTEGER PRIMARY KEY,
    "username" TEXT NOT NULL UNIQUE,
    "email" TEXT NOT NULL UNIQUE,
    "password_hash" TEXT NOT NULL,
    "onboarding_genres" TEXT,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "latest_swipe_song_id" INTEGER,
    FOREIGN KEY ("latest_swipe_song_id") REFERENCES "songs"("song_id")
);

CREATE TABLE IF NOT EXISTS "swipes" (
    "swipe_id" INTEGER PRIMARY KEY,
    "user_id" INTEGER NOT NULL,
    "song_id" INTEGER NOT NULL,
    "like" BOOLEAN NOT NULL,
    "timestamp" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("user_id") REFERENCES "users"("user_id"),
    FOREIGN KEY ("song_id") REFERENCES "songs"("song_id")
);

CREATE TABLE IF NOT EXISTS "recommendations" (
    "user_id" INTEGER NOT NULL,
    "song_id" INTEGER NOT NULL,
    "score" REAL NOT NULL,
    "generated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("user_id") REFERENCES "users"("user_id"),
    FOREIGN KEY ("song_id") REFERENCES "songs"("song_id")
);