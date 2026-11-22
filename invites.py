"""Inviting relatives to a family tree."""

import re
from urllib.parse import quote

from accounts import unique_id
from db import get_db

RELATIONSHIPS = {
    "grandparent": "Grandparent",
    "parent": "Parent",
    "aunt-uncle": "Aunt or uncle",
    "sibling": "Brother or sister",
    "cousin": "Cousin",
    "other": "Someone else",
}


class InviteError(Exception):
    """Something the person can fix, shown on the Family page."""


def _clean_contact(contact):
    """An email address or phone number, or an error."""
    contact = contact.strip()
    if "@" in contact and "." in contact.split("@")[-1]:
        return contact.lower()
    digits = re.sub(r"\D", "", contact)
    if 7 <= len(digits) <= 15:
        return contact
    raise InviteError("Enter an email address or a phone number.")


def create_invite(family_id, inviter_id, name, relationship, contact):
    """Add someone to the tree as a pending member. Returns their person id."""
    parts = name.split()
    if len(parts) < 2:
        raise InviteError("Enter their first and last name, so their account links up when they join.")
    first, last = parts[0], " ".join(parts[1:])
    contact = _clean_contact(contact)
    relationship = relationship if relationship in RELATIONSHIPS else "other"

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT m.role, p.first_name FROM members m JOIN people p ON p.id = m.person_id
               WHERE m.family_id = %s AND lower(p.first_name) = lower(%s) AND lower(p.last_name) = lower(%s)""",
            (family_id, first, last))
        existing = cur.fetchone()
        if existing:
            if existing["role"] == "pending":
                raise InviteError(f"{existing['first_name']} has already been invited.")
            raise InviteError(f"{existing['first_name']} is already in this tree.")

        person_id = unique_id(cur, "people", first)
        cur.execute(
            "INSERT INTO people (id, first_name, last_name, side) VALUES (%s, %s, %s, 'both')",
            (person_id, first, last))
        cur.execute(
            """INSERT INTO members (family_id, person_id, role, position, invited_by, invited_at,
                                    invited_contact, invited_relationship)
               VALUES (%s, %s, 'pending', 1000, %s, now(), %s, %s)""",
            (family_id, person_id, inviter_id, contact, relationship))
    conn.commit()
    return person_id


def get_invite(family_id, person_id, viewer_id):
    """A pending invite the viewer sent, with ready-made email and text links."""
    with get_db().cursor() as cur:
        cur.execute(
            """SELECT m.*, p.first_name, p.last_name, f.name AS family_name, f.invite_code
               FROM members m
               JOIN people p ON p.id = m.person_id
               JOIN families f ON f.id = m.family_id
               WHERE m.family_id = %s AND m.person_id = %s AND m.role = 'pending' AND m.invited_by = %s""",
            (family_id, person_id, viewer_id))
        invite = cur.fetchone()
    if not invite:
        return None

    link = f"branchspoken.com/join?code={invite['invite_code']}"
    message = (f"Hi {invite['first_name']}, I added you to {invite['family_name']} on Branch Spoken, "
               f"where our family keeps the stories we tell about each other. "
               f"Join with this link and the name {invite['first_name']} {invite['last_name']}: https://{link}")
    contact = invite["invited_contact"]
    if "@" in contact:
        send_link = f"mailto:{quote(contact)}?subject={quote('Join our family tree')}&body={quote(message)}"
        send_label = "Send by email"
    else:
        send_link = f"sms:{re.sub(r'[^0-9+]', '', contact)}?&body={quote(message)}"
        send_label = "Send by text"
    return dict(invite, link=link, message=message, send_link=send_link, send_label=send_label)


def cancel_invite(family_id, person_id, viewer_id, viewer_is_keeper):
    """Remove a pending invite. Only the person who sent it or the Keeper can."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT invited_by FROM members WHERE family_id = %s AND person_id = %s AND role = 'pending'",
            (family_id, person_id))
        invite = cur.fetchone()
        if not invite or not (viewer_is_keeper or invite["invited_by"] == viewer_id):
            return False

        cur.execute("DELETE FROM members WHERE family_id = %s AND person_id = %s", (family_id, person_id))

        # if nothing else refers to them, remove the placeholder person too
        cur.execute(
            """SELECT EXISTS (SELECT 1 FROM members WHERE person_id = %(p)s)
                   OR EXISTS (SELECT 1 FROM users WHERE person_id = %(p)s)
                   OR EXISTS (SELECT 1 FROM parents WHERE child_id = %(p)s OR parent_id = %(p)s)
                   OR EXISTS (SELECT 1 FROM people WHERE spouse_id = %(p)s)
                   OR EXISTS (SELECT 1 FROM stories WHERE teller_id = %(p)s)
                   OR EXISTS (SELECT 1 FROM story_subjects WHERE person_id = %(p)s)
                   OR EXISTS (SELECT 1 FROM family_branches WHERE root_id = %(p)s) AS in_use""",
            {"p": person_id})
        if not cur.fetchone()["in_use"]:
            cur.execute("DELETE FROM people WHERE id = %s", (person_id,))
    conn.commit()
    return True
