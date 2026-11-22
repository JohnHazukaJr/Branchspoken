"""Database connection and loading.

Reads the family out of PostgreSQL in the same shape the sample data in
data.py used, so family.py can work out relationships the same way.
"""

import os

import psycopg
from dotenv import load_dotenv
from flask import g
from psycopg.rows import dict_row

load_dotenv()


def get_db():
    """One connection per request, closed when the request ends."""
    if "db" not in g:
        g.db = psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)
    return g.db


def close_db(error=None):
    conn = g.pop("db", None)
    if conn is not None:
        if error is None:
            conn.commit()
        conn.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def _rows(sql, params=()):
    with get_db().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def load_family_data():
    """Everything family.py needs, read in one go."""
    people = {}
    for row in _rows("SELECT * FROM people ORDER BY born, id"):
        person = {
            "first": row["first_name"], "last": row["last_name"], "sex": row["sex"],
            "side": row["side"], "born": row["born"], "birthplace": row["birthplace"],
            "parents": [], "spouse": row["spouse_id"],
            "photo": row["photo"], "photo_caption": row["photo_caption"],
        }
        if row["died"]:
            person["died"] = row["died"]
            person["deathplace"] = row["deathplace"]
        people[row["id"]] = person
    # father first, then mother
    for row in _rows("""SELECT pa.child_id, pa.parent_id FROM parents pa
                        JOIN people pe ON pe.id = pa.parent_id
                        ORDER BY pa.child_id, pe.sex DESC"""):
        people[row["child_id"]]["parents"].append(row["parent_id"])

    families = {}
    for row in _rows("SELECT * FROM families ORDER BY id"):
        families[row["id"]] = {
            "name": row["name"], "branches": [],
            "meet": [row["meet_a_id"], row["meet_b_id"]] if row["meet_a_id"] else None,
            "married": row["married"], "invite_code": row["invite_code"],
        }
    for row in _rows("SELECT * FROM family_branches ORDER BY family_id, position"):
        families[row["family_id"]]["branches"].append(
            {"side": row["side"], "title": row["title"], "root": row["root_id"]})

    records = {}
    for row in _rows("SELECT * FROM records ORDER BY position"):
        records[row["id"]] = {
            "title": row["title"], "kind": row["kind"], "year": row["year_label"],
            "people": row["people_label"], "image": row["image"], "alt": row["alt"],
            "waiting": row["waiting"],
        }

    stories = {}
    for row in _rows("SELECT * FROM stories ORDER BY added DESC, id"):
        story = {
            "title": row["title"], "type": row["type"], "teller": row["teller_id"],
            "subjects": [], "records": [],
            "era": row["era"], "year": row["year"], "place": row["place_id"],
            "added": row["added"].isoformat(), "excerpt": row["excerpt"],
            "body": [p for p in row["body"].split("\n\n") if p.strip()],
        }
        # only copy the optional fields a story actually has
        for column in ["minutes", "detail", "photo", "photo_alt", "photo_caption",
                       "audio", "audio_length", "records_note"]:
            if row[column] is not None:
                story[column] = row[column]
        stories[row["id"]] = story
    for row in _rows("SELECT story_id, person_id FROM story_subjects ORDER BY story_id, position"):
        stories[row["story_id"]]["subjects"].append(row["person_id"])
    for row in _rows("SELECT story_id, record_id FROM story_records ORDER BY story_id, position"):
        stories[row["story_id"]]["records"].append(row["record_id"])

    places = {}
    for row in _rows("SELECT * FROM places ORDER BY map_x DESC"):
        places[row["id"]] = {
            "name": row["name"], "short": row["short_name"], "side": row["side"],
            "families": row["families"], "years": row["years"], "x": row["map_x"], "y": row["map_y"],
        }

    journeys = [
        {"year": r["year"], "from": r["from_place"], "to": r["to_place"], "side": r["side"],
         "text": r["text"], "story": r["story_id"], "path": r["path"]}
        for r in _rows("SELECT * FROM journeys ORDER BY year")
    ]

    events = []
    for r in _rows("SELECT * FROM events ORDER BY year"):
        event = {"year": r["year"], "title": r["title"], "side": r["side"]}
        for column in ["story", "note", "anchor"]:
            value = r["story_id"] if column == "story" else r[column]
            if value:
                event[column] = value
        events.append(event)

    members = [
        {"person": r["person_id"], "role": r["role"], "note": r["note"]}
        for r in _rows("SELECT * FROM members WHERE family_id = %s ORDER BY position", ("miller",))
    ]

    questions = [r["text"] for r in _rows("SELECT text FROM questions ORDER BY position")]

    return {
        "PEOPLE": people, "FAMILIES": families, "STORIES": stories, "RECORDS": records,
        "PLACES": places, "JOURNEYS": journeys, "EVENTS": events, "MEMBERS": members,
        "QUESTIONS": questions,
    }
