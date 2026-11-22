"""Accounts: signing up, signing in and joining a family tree."""

import re
import secrets

from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db

MIN_PASSWORD_LENGTH = 8


class AccountError(Exception):
    """Something the person filling in the form can fix, shown on the page."""


# ---------- Looking things up ----------

def find_user(email):
    with get_db().cursor() as cur:
        cur.execute("SELECT * FROM users WHERE lower(email) = lower(%s)", (email.strip(),))
        return cur.fetchone()


def check_login(email, password):
    """The user if the email and password match, otherwise None."""
    user = find_user(email)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def find_family_by_code(code):
    with get_db().cursor() as cur:
        cur.execute("SELECT * FROM families WHERE upper(invite_code) = upper(%s)", (code.strip(),))
        return cur.fetchone()


def family_keeper(family_id):
    """The person who started a tree, for 'Thomas Miller invited you'."""
    with get_db().cursor() as cur:
        cur.execute(
            """SELECT p.first_name, p.last_name FROM members m
               JOIN people p ON p.id = m.person_id
               WHERE m.family_id = %s AND m.role = 'keeper'
               ORDER BY m.position LIMIT 1""",
            (family_id,))
        return cur.fetchone()


def families_of(person_id):
    """The trees someone belongs to, the one they keep first."""
    with get_db().cursor() as cur:
        cur.execute(
            """SELECT family_id FROM members
               WHERE person_id = %s AND role <> 'pending'
               ORDER BY role = 'keeper' DESC, family_id""",
            (person_id,))
        return [row["family_id"] for row in cur.fetchall()]


# ---------- Creating things ----------

def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def unique_id(cur, table, base):
    """'ruth', or 'ruth-2' if that's taken, for page addresses."""
    base = _slug(base) or table.rstrip("s")
    candidate, number = base, 2
    while True:
        cur.execute(f"SELECT 1 FROM {table} WHERE id = %s", (candidate,))
        if not cur.fetchone():
            return candidate
        candidate, number = f"{base}-{number}", number + 1


# no 0/O or 1/I/L, so codes are easy to read out over the phone
CODE_LETTERS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _invite_code(cur, tree_name):
    """MILLER-K7QF-29XD: the family name and eight random characters.

    About a trillion possible codes per name, so they can't be guessed.
    """
    words = [w for w in re.findall(r"[A-Za-z]+", tree_name) if w.lower() not in ("the", "family")]
    word = (words[-1] if words else "TREE").upper()[:12]
    while True:
        random_part = "".join(secrets.choice(CODE_LETTERS) for _ in range(8))
        code = f"{word}-{random_part[:4]}-{random_part[4:]}"
        cur.execute("SELECT 1 FROM families WHERE invite_code = %s", (code,))
        if not cur.fetchone():
            return code


def new_invite_code(family_id):
    """Replace a tree's invite code, so an old link that got shared stops working."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM families WHERE id = %s", (family_id,))
        family = cur.fetchone()
        code = _invite_code(cur, family["name"])
        cur.execute("UPDATE families SET invite_code = %s WHERE id = %s", (code, family_id))
    conn.commit()
    return code


def role_in(person_id, family_id):
    """keeper, editor, storyteller, pending or None."""
    with get_db().cursor() as cur:
        cur.execute("SELECT role FROM members WHERE person_id = %s AND family_id = %s",
                    (person_id, family_id))
        row = cur.fetchone()
        return row["role"] if row else None


def _check_new_account(email, password):
    if "@" not in email:
        raise AccountError("Enter an email address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AccountError(f"Your password needs at least {MIN_PASSWORD_LENGTH} characters.")
    if find_user(email):
        raise AccountError("There's already an account with that email. Try signing in instead.")


def _create_person(cur, first, last, born=None):
    person_id = unique_id(cur, "people", first)
    cur.execute(
        # sex is left empty, so relationship words stay neutral ("parent", "sibling")
        """INSERT INTO people (id, first_name, last_name, side, born)
           VALUES (%s, %s, %s, 'both', %s)""",
        (person_id, first.strip(), last.strip(), born))
    return person_id


def _create_user(cur, person_id, email, password):
    cur.execute(
        "INSERT INTO users (person_id, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
        (person_id, email.strip().lower(), generate_password_hash(password)))
    return cur.fetchone()["id"]


def sign_up(first, last, born, email, password, tree_name):
    """Create the person, their new tree and their account.

    Returns (user_id, person_id, family_id).
    """
    if not first.strip() or not last.strip():
        raise AccountError("Enter your first and last name.")
    if not tree_name.strip():
        raise AccountError("Give your tree a name.")
    _check_new_account(email, password)

    conn = get_db()
    with conn.cursor() as cur:
        person_id = _create_person(cur, first, last, born)

        family_id = unique_id(cur, "families", tree_name)
        cur.execute(
            "INSERT INTO families (id, name, invite_code) VALUES (%s, %s, %s)",
            (family_id, tree_name.strip(), _invite_code(cur, tree_name)))
        cur.execute(
            """INSERT INTO family_branches (family_id, position, side, title, root_id)
               VALUES (%s, 0, 'both', %s, %s)""",
            (family_id, tree_name.strip(), person_id))
        cur.execute(
            """INSERT INTO members (family_id, person_id, role, note)
               VALUES (%s, %s, 'keeper', 'started the tree')""",
            (family_id, person_id))

        user_id = _create_user(cur, person_id, email, password)
    conn.commit()
    return user_id, person_id, family_id


def join(code, first, last, email, password):
    """Create an account in an existing tree.

    If the tree already has a pending invite for someone with this name,
    the account takes over that person, so stories about them stay linked.
    Returns (user_id, person_id, family_id).
    """
    family = find_family_by_code(code)
    if not family:
        raise AccountError("We couldn't find that invite code. Check it and try again.")
    if not first.strip() or not last.strip():
        raise AccountError("Enter your first and last name.")
    _check_new_account(email, password)

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT m.person_id FROM members m
               JOIN people p ON p.id = m.person_id
               LEFT JOIN users u ON u.person_id = p.id
               WHERE m.family_id = %s AND m.role = 'pending' AND u.id IS NULL
                 AND lower(p.first_name) = lower(%s) AND lower(p.last_name) = lower(%s)""",
            (family["id"], first.strip(), last.strip()))
        invited = cur.fetchone()

        if invited:
            person_id = invited["person_id"]
            cur.execute(
                """UPDATE members SET role = 'storyteller', note = NULL
                   WHERE family_id = %s AND person_id = %s""",
                (family["id"], person_id))
        else:
            person_id = _create_person(cur, first, last)
            cur.execute(
                """INSERT INTO members (family_id, person_id, role, position)
                   VALUES (%s, %s, 'storyteller', 100)""",
                (family["id"], person_id))

        user_id = _create_user(cur, person_id, email, password)
    conn.commit()
    return user_id, person_id, family["id"]
