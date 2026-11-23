"""Adding relatives to a family tree and editing people's details."""

from datetime import date

from accounts import unique_id
from db import get_db
from memories import StoryError, save_upload

RELATIONS = {
    "parent": "Parent",
    "child": "Child",
    "spouse": "Husband or wife",
    "sibling": "Brother or sister",
}


class RelativeError(Exception):
    """Something the person can fix, shown on the form."""


# ---------- Checking the form ----------

def _year(form, field, label):
    value = form.get(field, "").strip()
    if not value:
        return None
    if not value.isdigit() or not 1500 <= int(value) <= date.today().year:
        raise RelativeError(f"{label} should be a year, like 1931.")
    return int(value)


def clean_details(form):
    """The person's details from the form, checked and tidied."""
    first = form.get("first_name", "").strip()[:60]
    last = form.get("last_name", "").strip()[:60]
    if not first or not last:
        raise RelativeError("Enter a first and last name.")

    sex = form.get("sex", "")
    born = _year(form, "born", "Year born")
    died = _year(form, "died", "Year died")
    if born and died and died < born:
        raise RelativeError("The year they died can't be before the year they were born.")

    return {
        "first_name": first,
        "last_name": last,
        "sex": sex if sex in ("f", "m") else None,
        "born": born,
        "birthplace": form.get("birthplace", "").strip()[:80] or None,
        "died": died,
        "deathplace": form.get("deathplace", "").strip()[:80] or None,
        "photo_caption": form.get("photo_caption", "").strip()[:80] or None,
    }


def _photo(files):
    """Save an uploaded photo, turning upload problems into form errors."""
    try:
        return save_upload(files.get("photo"), "image")
    except StoryError as problem:
        raise RelativeError(str(problem)) from problem


# ---------- Editing ----------

def update_person(person_id, form, files):
    details = clean_details(form)
    photo = _photo(files)

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE people SET first_name = %(first_name)s, last_name = %(last_name)s, sex = %(sex)s,
                                 born = %(born)s, birthplace = %(birthplace)s,
                                 died = %(died)s, deathplace = %(deathplace)s,
                                 photo_caption = %(photo_caption)s
               WHERE id = %(id)s""",
            dict(details, id=person_id))
        if photo:
            cur.execute("UPDATE people SET photo = %s WHERE id = %s", (photo, person_id))
    conn.commit()


# ---------- Adding to the tree ----------

def _create_person(cur, details, photo, side):
    person_id = unique_id(cur, "people", details["first_name"])
    cur.execute(
        """INSERT INTO people (id, first_name, last_name, sex, side, born, birthplace,
                               died, deathplace, photo, photo_caption)
           VALUES (%(id)s, %(first_name)s, %(last_name)s, %(sex)s, %(side)s, %(born)s, %(birthplace)s,
                   %(died)s, %(deathplace)s, %(photo)s, %(photo_caption)s)""",
        dict(details, id=person_id, side=side, photo=photo))
    return person_id


def _link_parent(cur, child_id, parent_id):
    cur.execute(
        "INSERT INTO parents (child_id, parent_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (child_id, parent_id))


def add_relative(anchor_id, relation, form, files, family_id, existing_id=None, also_spouse=True):
    """Add a parent, child, spouse or sibling of anchor_id. Returns the relative's person id.

    existing_id places someone already in the family (like an accepted invite)
    instead of creating a new person. The route checks it's allowed.
    """
    if relation not in RELATIONS:
        raise RelativeError("Choose who you're adding.")
    if existing_id == anchor_id:
        raise RelativeError("Someone can't be their own relative.")

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT first_name, side, spouse_id FROM people WHERE id = %s", (anchor_id,))
        anchor = cur.fetchone()
        cur.execute("SELECT parent_id FROM parents WHERE child_id = %s", (anchor_id,))
        anchor_parents = [row["parent_id"] for row in cur.fetchall()]
        name = anchor["first_name"]

        # check the relationship makes sense before creating anyone
        if relation == "parent" and len(anchor_parents) >= 2:
            raise RelativeError(f"{name} already has two parents on the tree.")
        if relation == "spouse" and anchor["spouse_id"]:
            raise RelativeError(f"{name} already has a husband or wife on the tree.")
        if relation == "sibling" and not anchor_parents:
            raise RelativeError(f"Add a parent for {name} first. Brothers and sisters are linked through their parents.")

        if existing_id:
            cur.execute("SELECT spouse_id FROM people WHERE id = %s", (existing_id,))
            if relation == "spouse" and cur.fetchone()["spouse_id"]:
                raise RelativeError("That person already has a husband or wife on the tree.")
            # draw them in the same branch as the person they're joining
            cur.execute("UPDATE people SET side = %s WHERE id = %s", (anchor["side"], existing_id))
            person_id = existing_id
        else:
            details = clean_details(form)
            person_id = _create_person(cur, details, _photo(files), anchor["side"])

        if relation == "parent":
            _link_parent(cur, anchor_id, person_id)
            # the other parent, if they don't have one yet, becomes their husband or wife
            if anchor_parents:
                other = anchor_parents[0]
                cur.execute("SELECT spouse_id FROM people WHERE id IN (%s, %s)", (other, person_id))
                if all(row["spouse_id"] is None for row in cur.fetchall()):
                    cur.execute("UPDATE people SET spouse_id = %s WHERE id = %s", (person_id, other))
                    cur.execute("UPDATE people SET spouse_id = %s WHERE id = %s", (other, person_id))
            # if the tree starts at this person, start it at the new parent instead
            cur.execute(
                "UPDATE family_branches SET root_id = %s WHERE family_id = %s AND root_id = %s",
                (person_id, family_id, anchor_id))

        elif relation == "child":
            _link_parent(cur, person_id, anchor_id)
            if also_spouse and anchor["spouse_id"]:
                _link_parent(cur, person_id, anchor["spouse_id"])

        elif relation == "spouse":
            cur.execute("UPDATE people SET spouse_id = %s WHERE id = %s", (person_id, anchor_id))
            cur.execute("UPDATE people SET spouse_id = %s WHERE id = %s", (anchor_id, person_id))

        elif relation == "sibling":
            for parent_id in anchor_parents:
                _link_parent(cur, person_id, parent_id)

    conn.commit()
    return person_id
