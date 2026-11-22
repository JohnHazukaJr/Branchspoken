"""Create the tables and load the sample family into PostgreSQL.

Run with:  python seed.py
Warning: this drops every table first, so anything added through the app is lost.
"""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from data import (EVENTS, FAMILIES, JOURNEYS, MEMBERS, PEOPLE, PLACES,
                  QUESTIONS, RECORDS, STORIES, USERS)

load_dotenv()

# records, places, journeys and events belong to this tree unless they say otherwise
DEFAULT_FAMILY = "miller"


def seed(conn):
    with conn.cursor() as cur:
        cur.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))

        # people first, then husbands and wives once everyone exists
        for pid, p in PEOPLE.items():
            cur.execute(
                """INSERT INTO people (id, first_name, last_name, sex, side, born, birthplace,
                                       died, deathplace, photo, photo_caption)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (pid, p["first"], p["last"], p["sex"], p["side"], p.get("born"), p.get("birthplace"),
                 p.get("died"), p.get("deathplace"), p.get("photo"), p.get("photo_caption")))
        for pid, p in PEOPLE.items():
            if p.get("spouse"):
                cur.execute("UPDATE people SET spouse_id = %s WHERE id = %s", (p["spouse"], pid))
            for parent in p.get("parents", []):
                cur.execute("INSERT INTO parents (child_id, parent_id) VALUES (%s, %s)", (pid, parent))

        for fid, f in FAMILIES.items():
            meet = f.get("meet") or [None, None]
            cur.execute(
                """INSERT INTO families (id, name, meet_a_id, meet_b_id, married, invite_code)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (fid, f["name"], meet[0], meet[1], f.get("married"), f["invite_code"]))
            for position, b in enumerate(f["branches"]):
                cur.execute(
                    """INSERT INTO family_branches (family_id, position, side, title, root_id)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (fid, position, b["side"], b["title"], b["root"]))

        for position, m in enumerate(MEMBERS):
            cur.execute(
                """INSERT INTO members (family_id, person_id, role, note, position, invited_by, invited_at)
                   VALUES (%s, %s, %s, %s, %s, %s,
                           CASE WHEN %s::int IS NULL THEN NULL ELSE now() - make_interval(days => %s::int) END)""",
                (m["family"], m["person"], m["role"], m.get("note"), position, m.get("invited_by"),
                 m.get("invited_days_ago"), m.get("invited_days_ago")))

        for u in USERS:
            cur.execute(
                "INSERT INTO users (person_id, email, password_hash) VALUES (%s, %s, %s)",
                (u["person"], u["email"], generate_password_hash(u["password"])))

        for place_id, p in PLACES.items():
            cur.execute(
                """INSERT INTO places (id, family_id, name, short_name, side, families, years, map_x, map_y)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (place_id, p.get("family", DEFAULT_FAMILY), p["name"], p["short"], p["side"], p["families"], p["years"], p["x"], p["y"]))

        for position, (rid, r) in enumerate(RECORDS.items()):
            cur.execute(
                """INSERT INTO records (id, family_id, title, kind, year_label, people_label, image, alt,
                                        waiting, position)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (rid, r.get("family", DEFAULT_FAMILY), r["title"], r["kind"], r["year"], r["people"], r["image"], r["alt"],
                 r.get("waiting"), position))

        for sid, s in STORIES.items():
            cur.execute(
                """INSERT INTO stories (id, title, type, teller_id, era, year, minutes, detail, place_id,
                                        added, excerpt, body, photo, photo_alt, photo_caption,
                                        audio, audio_length, records_note)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (sid, s["title"], s["type"], s["teller"], s.get("era"), s.get("year"), s.get("minutes"),
                 s.get("detail"), s.get("place"), s["added"], s.get("excerpt"), "\n\n".join(s["body"]),
                 s.get("photo"), s.get("photo_alt"), s.get("photo_caption"), s.get("audio"),
                 s.get("audio_length"), s.get("records_note")))
            for position, pid in enumerate(s["subjects"]):
                cur.execute(
                    "INSERT INTO story_subjects (story_id, person_id, position) VALUES (%s, %s, %s)",
                    (sid, pid, position))
            for position, rid in enumerate(s.get("records", [])):
                cur.execute(
                    "INSERT INTO story_records (story_id, record_id, position) VALUES (%s, %s, %s)",
                    (sid, rid, position))

        for j in JOURNEYS:
            cur.execute(
                """INSERT INTO journeys (family_id, year, from_place, to_place, side, text, story_id, path)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (j.get("family", DEFAULT_FAMILY), j["year"], j["from"], j["to"], j["side"], j["text"], j["story"], j["path"]))

        for e in EVENTS:
            cur.execute(
                """INSERT INTO events (family_id, year, title, side, story_id, note, anchor)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (e.get("family", DEFAULT_FAMILY), e["year"], e["title"], e["side"], e.get("story"), e.get("note"), e.get("anchor")))

        for position, text in enumerate(QUESTIONS, start=1):
            cur.execute("INSERT INTO questions (position, text) VALUES (%s, %s)", (position, text))


if __name__ == "__main__":
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        seed(conn)
    print(f"Loaded {len(PEOPLE)} people, {len(STORIES)} stories and {len(RECORDS)} records.")
    print("Demo accounts:", ", ".join(u["email"] for u in USERS), "(password: family-stories)")
