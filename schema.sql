-- Branch Spoken database
-- Running this file drops and recreates every table.

DROP TABLE IF EXISTS questions, events, journeys, story_records, story_subjects,
    stories, records, places, members, users, family_branches, families,
    parents, people CASCADE;


-- ---------- People and how they're related ----------

CREATE TABLE people (
    id            TEXT PRIMARY KEY,              -- used in page addresses, e.g. /relatives/ruth
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    sex           CHAR(1) CHECK (sex IN ('f', 'm')),   -- empty means use neutral words
    side          TEXT NOT NULL,                 -- family line: miller, sullivan or both
    born          INTEGER,
    birthplace    TEXT,
    died          INTEGER,
    deathplace    TEXT,
    spouse_id     TEXT REFERENCES people (id),
    photo         TEXT,
    photo_caption TEXT
);

CREATE TABLE parents (
    child_id  TEXT NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    parent_id TEXT NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    PRIMARY KEY (child_id, parent_id)
);


-- ---------- Family trees and who belongs to them ----------

CREATE TABLE families (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    meet_a_id   TEXT REFERENCES people (id),    -- the couple where two lines join
    meet_b_id   TEXT REFERENCES people (id),
    married     INTEGER,
    invite_code TEXT NOT NULL UNIQUE
);

CREATE TABLE family_branches (
    family_id TEXT NOT NULL REFERENCES families (id) ON DELETE CASCADE,
    position  INTEGER NOT NULL,
    side      TEXT NOT NULL,
    title     TEXT NOT NULL,
    root_id   TEXT NOT NULL REFERENCES people (id),
    PRIMARY KEY (family_id, position)
);

CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    person_id     TEXT UNIQUE REFERENCES people (id),
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE members (
    family_id TEXT NOT NULL REFERENCES families (id) ON DELETE CASCADE,
    person_id TEXT NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    role      TEXT NOT NULL CHECK (role IN ('keeper', 'editor', 'storyteller', 'pending')),
    note      TEXT,
    position  INTEGER NOT NULL DEFAULT 0,
    -- filled in for invites that haven't been accepted yet
    invited_by           TEXT REFERENCES people (id) ON DELETE SET NULL,
    invited_at           TIMESTAMPTZ,
    invited_contact      TEXT,              -- email or phone, only shown to whoever sent the invite
    invited_relationship TEXT,
    PRIMARY KEY (family_id, person_id)
);


-- ---------- Places ----------

CREATE TABLE places (
    id         TEXT PRIMARY KEY,
    family_id  TEXT NOT NULL REFERENCES families (id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    short_name TEXT NOT NULL,
    side       TEXT NOT NULL,
    families   TEXT,
    years      TEXT,
    map_x      INTEGER NOT NULL,                -- pin position on the map, in percent
    map_y      INTEGER NOT NULL
);


-- ---------- Records, photos and letters ----------

CREATE TABLE records (
    id           TEXT PRIMARY KEY,
    family_id    TEXT NOT NULL REFERENCES families (id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    kind         TEXT NOT NULL CHECK (kind IN ('photo', 'record', 'letter', 'document')),
    year_label   TEXT,
    people_label TEXT,
    image        TEXT,
    alt          TEXT,
    waiting      TEXT,                          -- a story we could narrate from it
    position     INTEGER NOT NULL DEFAULT 0
);


-- ---------- Stories ----------

CREATE TABLE stories (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    type          TEXT NOT NULL CHECK (type IN ('voice', 'photo', 'record', 'text')),
    teller_id     TEXT REFERENCES people (id),  -- empty for stories narrated from a record
    era           TEXT,
    year          INTEGER,
    minutes       INTEGER,
    detail        TEXT,
    place_id      TEXT REFERENCES places (id),
    added         DATE NOT NULL DEFAULT CURRENT_DATE,
    excerpt       TEXT,
    body          TEXT NOT NULL,                -- paragraphs separated by a blank line
    photo         TEXT,
    photo_alt     TEXT,
    photo_caption TEXT,
    audio         TEXT,
    audio_length  TEXT,
    records_note  TEXT
);

-- who a story is about; position 0 is the main person
CREATE TABLE story_subjects (
    story_id  TEXT NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
    person_id TEXT NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    position  INTEGER NOT NULL,
    PRIMARY KEY (story_id, person_id)
);

CREATE TABLE story_records (
    story_id  TEXT NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
    record_id TEXT NOT NULL REFERENCES records (id) ON DELETE CASCADE,
    position  INTEGER NOT NULL,
    PRIMARY KEY (story_id, record_id)
);


-- ---------- Map journeys and timeline events ----------

CREATE TABLE journeys (
    id         SERIAL PRIMARY KEY,
    family_id  TEXT NOT NULL REFERENCES families (id) ON DELETE CASCADE,
    year       INTEGER NOT NULL,
    from_place TEXT NOT NULL REFERENCES places (id),
    to_place   TEXT NOT NULL REFERENCES places (id),
    side       TEXT NOT NULL,
    text       TEXT NOT NULL,
    story_id   TEXT REFERENCES stories (id),
    path       TEXT NOT NULL                    -- SVG curve drawn on the map
);

CREATE TABLE events (
    id        SERIAL PRIMARY KEY,
    family_id TEXT NOT NULL REFERENCES families (id) ON DELETE CASCADE,
    year     INTEGER NOT NULL,
    title    TEXT NOT NULL,
    side     TEXT NOT NULL,
    story_id TEXT REFERENCES stories (id),
    note     TEXT,
    anchor   TEXT
);


-- ---------- Interview questions for the recorder ----------

CREATE TABLE questions (
    position INTEGER PRIMARY KEY,
    text     TEXT NOT NULL
);
