"""Saving new stories from the recorder."""

import re
import secrets
from datetime import date
from pathlib import Path

from db import get_db

# uploads live outside static/ so they're only served to the family (see /media in app.py)
UPLOAD_DIR = Path(__file__).with_name("uploads")


class StoryError(Exception):
    """Something the person can fix, shown on the recorder page."""


# ---------- Checking uploads ----------

def _kind_of_file(start):
    """Work out the real file type from its first bytes, whatever its name says."""
    if start.startswith(b"\xff\xd8\xff"):
        return "image", "jpg"
    if start.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", "png"
    if start.startswith((b"GIF87a", b"GIF89a")):
        return "image", "gif"
    if start[:4] == b"RIFF" and start[8:12] == b"WEBP":
        return "image", "webp"
    if start.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio", "webm"
    if start.startswith(b"OggS"):
        return "audio", "ogg"
    if start[:4] == b"RIFF" and start[8:12] == b"WAVE":
        return "audio", "wav"
    if start.startswith(b"ID3") or (len(start) > 1 and start[0] == 0xFF and start[1] & 0xE0 == 0xE0):
        return "audio", "mp3"
    if start[4:8] == b"ftyp":
        return "audio", "m4a"
    return None, None


def save_upload(file, expected):
    """Save an uploaded audio or image file under a random name.

    Returns the path to store on the story, or None if nothing was uploaded.
    """
    if not file or not file.filename:
        return None

    start = file.stream.read(16)
    file.stream.seek(0)
    kind, extension = _kind_of_file(start)
    if kind != expected:
        if expected == "audio":
            raise StoryError("That recording isn't an audio file we can play. Try MP3, M4A, WAV, OGG or WebM.")
        raise StoryError("That photo isn't an image we can show. Try JPG, PNG, GIF or WebP.")

    UPLOAD_DIR.mkdir(exist_ok=True)
    name = f"{secrets.token_urlsafe(16)}.{extension}"
    file.save(UPLOAD_DIR / name)
    return f"uploads/{name}"


# ---------- Turning the form into a story ----------

def _unique_story_id(cur, title):
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "story"
    candidate, number = base, 2
    while True:
        cur.execute("SELECT 1 FROM stories WHERE id = %s", (candidate,))
        if not cur.fetchone():
            return candidate
        candidate, number = f"{base}-{number}", number + 1


def _paragraphs(transcript):
    """Split the transcript on blank lines, or on single lines if there are none."""
    text = transcript.replace("\r\n", "\n").strip()
    parts = re.split(r"\n\s*\n", text) if "\n\n" in text else text.split("\n")
    return [" ".join(p.split()) for p in parts if p.strip()]


def _excerpt(paragraphs):
    if not paragraphs:
        return None
    first = re.split(r"(?<=[.!?])\s", paragraphs[0], maxsplit=1)[0]
    return first if len(first) <= 160 else first[:157].rstrip() + "..."


def _match_place(places, typed):
    """'Boston' or 'Boston, Massachusetts' finds the Boston pin on the map."""
    typed = typed.strip().lower()
    if not typed:
        return None
    for place_id, place in places.items():
        if typed in (place["name"].lower(), place["short"].lower()) or typed.startswith(place["short"].lower()):
            return place_id
    return None


def _length(seconds):
    minutes, seconds = divmod(seconds, 60)
    if minutes and seconds:
        return f"{minutes} min {seconds} sec"
    return f"{minutes} min" if minutes else f"{seconds} sec"


def save_memory(form, files, teller_id, subjects, places, record_id=None):
    """Create a story from the recorder form. Returns the new story's id.

    teller_id and subjects must already be checked as people the viewer can see.
    """
    title = form.get("title", "").strip()[:120]
    paragraphs = _paragraphs(form.get("transcript", ""))
    if not title:
        raise StoryError("Give the story a title.")
    if not subjects:
        raise StoryError("Pick at least one person the story is about.")

    audio = save_upload(files.get("audio"), "audio")
    photo = save_upload(files.get("photo"), "image")
    if not (paragraphs or audio or photo):
        raise StoryError("Record something, write it down or add a photo before saving.")

    story_type = "voice" if audio else "photo" if photo and not paragraphs else "text"
    when = form.get("when", "").strip()[:60]
    year = re.search(r"\b(1[6-9]\d\d|20\d\d)\b", when)

    seconds = int(form["duration"]) if form.get("duration", "").isdigit() else 0
    if not paragraphs:
        paragraphs = ["No transcript yet."] if audio else [title]

    conn = get_db()
    with conn.cursor() as cur:
        story_id = _unique_story_id(cur, title)
        cur.execute(
            """INSERT INTO stories (id, title, type, teller_id, era, year, minutes, place_id, added,
                                    excerpt, body, photo, photo_alt, photo_caption, audio, audio_length)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (story_id, title, story_type, teller_id, when or None,
             int(year.group(1)) if year else None,
             max(1, round(seconds / 60)) if audio and seconds else None,
             _match_place(places, form.get("place", "")), date.today(),
             _excerpt(paragraphs), "\n\n".join(paragraphs),
             photo, title if photo else None, title if photo else None,
             audio, _length(seconds) if audio and seconds else None))
        for position, person_id in enumerate(subjects):
            cur.execute(
                "INSERT INTO story_subjects (story_id, person_id, position) VALUES (%s, %s, %s)",
                (story_id, person_id, position))
        if record_id:
            cur.execute(
                "INSERT INTO story_records (story_id, record_id, position) VALUES (%s, %s, 0)",
                (story_id, record_id))
    conn.commit()
    return story_id
