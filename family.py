"""Works out relationships, story counts and page data from the family data."""

from datetime import datetime, timezone

from db import load_family_data

# Who is signed in, set by refresh() from the login session
VIEWER_ID = None

# Total distance of the journeys on the map
JOURNEY_MILES = 4600

# Filled in from the database by refresh() at the start of every request
PEOPLE, FAMILIES, STORIES, RECORDS, PLACES = {}, {}, {}, {}, {}
JOURNEYS, EVENTS, MEMBERS, QUESTIONS = [], [], [], []

# The trees the viewer belongs to, and everyone in them.
# Nobody outside these trees is shown to the viewer.
VIEWER_FAMILIES = []
VIEWER_ROLES = {}          # family_id -> the viewer's role in it
VISIBLE = set()


def refresh(viewer_id=None):
    """Reload the family from the database so new stories show up right away."""
    globals().update(load_family_data())
    globals()["VIEWER_ID"] = viewer_id

    families = []
    for m in MEMBERS:
        if m["person"] == viewer_id and m["role"] != "pending" and m["family"] not in families:
            families.append(m["family"])
    visible = set()
    for family_id in families:
        visible |= tree_people(family_id)
        visible |= {m["person"] for m in MEMBERS if m["family"] == family_id}
    globals()["VIEWER_FAMILIES"] = families
    globals()["VIEWER_ROLES"] = {m["family"]: m["role"] for m in MEMBERS if m["person"] == viewer_id}
    globals()["VISIBLE"] = visible


def can_see(person_id):
    return person_id in VISIBLE


def families_with(person_id):
    """The viewer's trees that include this person, on the tree or as a member."""
    return [f for f in VIEWER_FAMILIES
            if person_id in tree_people(f) or person_id in {m["person"] for m in MEMBERS if m["family"] == f}]


def can_add_relatives(person_id):
    """Keepers and Editors can add relatives to anyone in their trees."""
    return any(VIEWER_ROLES.get(f) in ("keeper", "editor") for f in families_with(person_id))


def can_edit_person(person_id):
    """Keepers and Editors can edit anyone in their trees, everyone can edit themselves."""
    return person_id == VIEWER_ID or can_add_relatives(person_id)


def unplaced_members(family_id, exclude=()):
    """Members who aren't drawn on the tree yet, like an accepted invite, to place as a relative."""
    on_tree = tree_people(family_id)
    ids = [m["person"] for m in MEMBERS
           if m["family"] == family_id and m["person"] not in on_tree and m["person"] not in exclude]
    return [get_person(pid) for pid in ids]


def can_see_story(story_id):
    story = STORIES.get(story_id)
    return bool(story) and bool(VISIBLE & set(story["subjects"]))


def can_see_media(path):
    """True if an uploaded file belongs to a story the viewer can see."""
    return (any(path in (s.get("audio"), s.get("photo")) and can_see_story(sid)
                for sid, s in STORIES.items())
            or any(p.get("photo") == path and can_see(pid) for pid, p in PEOPLE.items()))


# ---------- People ----------

def get_person(person_id):
    """A person with their id and display names filled in, or None."""
    if person_id not in PEOPLE:
        return None
    p = dict(PEOPLE[person_id], id=person_id)
    p["name"] = f"{p['first']} {p['last']}"
    p["pronoun"] = {"f": "her", "m": "his"}.get(p["sex"], "their")
    p["object"] = {"f": "her", "m": "him"}.get(p["sex"], "them")
    return p


def parents_of(person_id):
    return PEOPLE[person_id].get("parents", [])


def children_of(*parent_ids):
    """Children whose parents are exactly these people, oldest first."""
    wanted = set(parent_ids)
    kids = [pid for pid, p in PEOPLE.items() if set(p.get("parents", [])) == wanted]
    return sorted(kids, key=lambda pid: PEOPLE[pid]["born"] or 9999)


def all_children_of(person_id):
    kids = [pid for pid, p in PEOPLE.items() if person_id in p.get("parents", [])]
    return sorted(kids, key=lambda pid: PEOPLE[pid]["born"] or 9999)


def siblings_of(person_id):
    mine = set(parents_of(person_id))
    if not mine:
        return []
    return [pid for pid, p in PEOPLE.items()
            if pid != person_id and mine & set(p.get("parents", []))]


def spouse_of(person_id):
    return PEOPLE[person_id].get("spouse")


# ---------- Relationships ----------

# (male, female, neutral) - the neutral word is used when sex isn't set
WORDS = {
    "spouse": ("husband", "wife", "spouse"),
    "parent": ("father", "mother", "parent"),
    "child": ("son", "daughter", "child"),
    "sibling": ("brother", "sister", "sibling"),
    "grandparent": ("grandfather", "grandmother", "grandparent"),
    "great-grandparent": ("great-grandfather", "great-grandmother", "great-grandparent"),
    "grandchild": ("grandson", "granddaughter", "grandchild"),
    "aunt-uncle": ("uncle", "aunt", "aunt or uncle"),
    "great-aunt-uncle": ("great-uncle", "great-aunt", "great-aunt or uncle"),
    "niece-nephew": ("nephew", "niece", "niece or nephew"),
    "cousin": ("cousin", "cousin", "cousin"),
    "parent-in-law": ("father-in-law", "mother-in-law", "parent-in-law"),
    "sibling-in-law": ("brother-in-law", "sister-in-law", "sibling-in-law"),
    "child-in-law": ("son-in-law", "daughter-in-law", "child-in-law"),
}


def _word(kind, person_id):
    male, female, neutral = WORDS[kind]
    return {"m": male, "f": female}.get(PEOPLE[person_id]["sex"], neutral)


def _side(parent_id):
    sex = PEOPLE[parent_id]["sex"]
    if sex in ("m", "f"):
        return "father's side" if sex == "m" else "mother's side"
    return f"{PEOPLE[parent_id]['first']}'s side"


def relation(from_id, to_id):
    """What to_id is to from_id, e.g. ("grandmother", "father's side").

    The side is only given for grandparents, aunts, uncles and cousins.
    """
    if from_id == to_id:
        return ("you", None)
    if spouse_of(from_id) == to_id:
        return (_word("spouse", to_id), None)
    if to_id in parents_of(from_id):
        return (_word("parent", to_id), None)
    if to_id in all_children_of(from_id):
        return (_word("child", to_id), None)
    if to_id in siblings_of(from_id):
        return (_word("sibling", to_id), None)

    for parent in parents_of(from_id):
        if to_id in parents_of(parent):
            return (_word("grandparent", to_id), _side(parent))
        if to_id in siblings_of(parent):
            return (_word("aunt-uncle", to_id), _side(parent))
        if any(spouse_of(s) == to_id for s in siblings_of(parent)):
            return (_word("aunt-uncle", to_id), _side(parent))
        for aunt_or_uncle in siblings_of(parent):
            if to_id in all_children_of(aunt_or_uncle):
                return (_word("cousin", to_id), _side(parent))
        for grandparent in parents_of(parent):
            if to_id in parents_of(grandparent):
                return (_word("great-grandparent", to_id), _side(parent))
            if to_id in siblings_of(grandparent):
                return (_word("great-aunt-uncle", to_id), _side(parent))

    for child in all_children_of(from_id):
        if to_id in all_children_of(child):
            return (_word("grandchild", to_id), None)
        if spouse_of(child) == to_id:
            return (_word("child-in-law", to_id), None)
    for sibling in siblings_of(from_id):
        if to_id in all_children_of(sibling):
            return (_word("niece-nephew", to_id), None)

    spouse = spouse_of(from_id)
    if spouse and to_id in parents_of(spouse):
        return (_word("parent-in-law", to_id), None)
    if spouse and to_id in siblings_of(spouse):
        return (_word("sibling-in-law", to_id), None)
    if any(spouse_of(s) == to_id for s in siblings_of(from_id)):
        return (_word("sibling-in-law", to_id), None)

    return ("relative", None)


def relation_to_viewer(person_id):
    """'Your grandmother · father's side', 'Your sister' or 'This is you'."""
    word, side = relation(VIEWER_ID, person_id)
    if word == "you":
        return "This is you"
    label = f"Your {word}" if word != "relative" else "Your relative"
    return f"{label} · {side}" if side else label


# ---------- Stories ----------

VERBS = {"voice": "Told by", "text": "Written by", "photo": "Shared by", "record": "Narrated"}


def get_story(story_id):
    """A story with its people looked up and its byline worked out, or None."""
    if story_id not in STORIES:
        return None
    s = dict(STORIES[story_id], id=story_id)
    s["subjects"] = [get_person(pid) for pid in s["subjects"]]
    s["main"] = s["subjects"][0]
    s["teller"] = get_person(s["teller"]) if s["teller"] else None
    s["verb"] = VERBS[s["type"]]
    s["records"] = [dict(RECORDS[rid], id=rid) for rid in s.get("records", [])]

    # "her daughter": how the teller is related to the main person
    s["teller_role"] = None
    if s["teller"] and s["teller"]["id"] != s["main"]["id"]:
        word, _ = relation(s["main"]["id"], s["teller"]["id"])
        if word != "relative":
            s["teller_role"] = f"{s['main']['pronoun']} {word}"

    # record stories have no teller: "Narrated from her birth record"
    if s["type"] == "record" and s["records"]:
        s["narrated"] = f"Narrated from {s['main']['pronoun']} {s['records'][0]['title'].lower()}"

    return s


def all_stories():
    """Every story the viewer can see, newest first."""
    ids = sorted(STORIES, key=lambda sid: STORIES[sid]["added"], reverse=True)
    return [get_story(sid) for sid in ids if can_see_story(sid)]


def stories_about(*person_ids):
    wanted = set(person_ids)
    return [s for s in all_stories() if wanted & {p["id"] for p in s["subjects"]}]


def stories_told_by(person_id):
    return [s for s in all_stories() if s["teller"] and s["teller"]["id"] == person_id]


def storytellers():
    return {s["teller"]["id"] for s in all_stories() if s["teller"]}


# ---------- Relative profile ----------

def profile(person_id):
    person = get_person(person_id)
    if not person:
        return None

    stories = stories_about(person_id)
    tellers = {s["teller"]["id"] for s in stories if s["teller"]}
    voice_minutes = sum(s.get("minutes", 0) for s in stories if s["type"] == "voice")

    family = []
    if spouse_of(person_id):
        if can_see(spouse_of(person_id)):
            family.append((_word("spouse", spouse_of(person_id)).capitalize(), [get_person(spouse_of(person_id))]))
    for label, ids in [("Parents", parents_of(person_id)),
                       ("Brothers and sisters", siblings_of(person_id)),
                       ("Children", all_children_of(person_id)),
                       ("Grandchildren", [g for c in all_children_of(person_id) for g in all_children_of(c)])]:
        ids = [pid for pid in ids if can_see(pid)]
        if ids:
            family.append((label, [get_person(pid) for pid in ids]))

    # suggest asking a living child (or the husband or wife) for a story
    ask = None
    for pid in all_children_of(person_id) + [spouse_of(person_id)]:
        if pid and pid != VIEWER_ID and can_see(pid) and "died" not in PEOPLE[pid]:
            asker = get_person(pid)
            word, _ = relation(person_id, pid)
            ask = {"person": asker, "text": f"{asker['first']} is {person['pronoun']} {word}. "
                                            f"Ask {asker['object']} for a story about {person['first']}?"}
            break

    return {
        "person": person,
        "relation": relation_to_viewer(person_id),
        "stories": stories,
        "teller_count": len(tellers),
        "voice_minutes": voice_minutes,
        "family": family,
        "ask": ask,
        "can_edit": can_edit_person(person_id),
        "can_add": can_add_relatives(person_id),
        # which "+ relative" buttons make sense for this person
        "add_options": {
            "parent": len(parents_of(person_id)) < 2,
            "child": True,
            "spouse": not spouse_of(person_id),
            "sibling": bool(parents_of(person_id)),
        },
    }


# ---------- Family tree ----------

def _node(person_ids):
    people = [get_person(pid) for pid in person_ids]
    years = " · ".join(f"b. {p['born']}" for p in people if p["born"])
    return {
        "people": people,
        "years": years,
        "story_count": len(stories_about(*person_ids)),
        "is_viewer": VIEWER_ID in person_ids,
    }


def _branch(person_id, side):
    """A person (with their husband or wife from the same line) and everyone below them."""
    ids = [person_id]
    spouse = spouse_of(person_id)
    if spouse and PEOPLE[spouse]["side"] == side:
        ids.append(spouse)
    node = _node(ids)
    node["children"] = [_branch(kid, side) for kid in children_of(*ids)]
    return node


def _collect(node, found):
    found.update(p["id"] for p in node["people"])
    for child in node.get("children", []):
        _collect(child, found)
    return found


def _people_below(person_id, side, found):
    ids = [person_id]
    spouse = spouse_of(person_id)
    if spouse and PEOPLE[spouse]["side"] == side:
        ids.append(spouse)
    found.update(ids)
    for kid in children_of(*ids):
        _people_below(kid, side, found)


def tree_people(family_id):
    """Everyone drawn on a family's tree."""
    family = FAMILIES[family_id]
    found = set()
    for branch in family["branches"]:
        _people_below(branch["root"], branch["side"], found)
    if family.get("meet"):
        found.update(family["meet"])
        found.update(children_of(*family["meet"]))
    return found


def family_tree(family_id):
    family = FAMILIES.get(family_id)
    if not family:
        return None

    branches = []
    people = set()
    for branch in family["branches"]:
        root = _branch(branch["root"], branch["side"])
        branches.append({"side": branch["side"], "title": branch["title"], "root": root})
        _collect(root, people)

    meet = None
    if family.get("meet"):
        couple = _node(family["meet"])
        couple["years"] = f"married {family['married']}"
        couple["children"] = [_node([kid]) for kid in children_of(*family["meet"])]
        meet = {"couple": couple, "married": family["married"]}
        _collect(couple, people)

    stories = [s for s in all_stories() if people & {p["id"] for p in s["subjects"]}]

    return {
        "id": family_id,
        "name": family["name"],
        "branches": branches,
        "meet": meet,
        "people_count": len(people),
        "story_count": len(stories),
        "latest": stories[:3],
    }


# ---------- Timeline ----------

def timeline():
    entries = []
    for pid in PEOPLE:
        if not can_see(pid) or not PEOPLE[pid]["born"]:
            continue
        p = get_person(pid)
        entries.append({
            "year": p["born"], "side": p["side"], "title": f"{p['first']} is born",
            "url_person": pid,
            "note": "That's you" if pid == VIEWER_ID else (p["birthplace"] or ""),
        })
    for event in EVENTS:
        if event["family"] not in VIEWER_FAMILIES:
            continue
        entry = dict(event)
        if event.get("story"):
            story = get_story(event["story"])
            teller = story["teller"]["first"] if story["teller"] else "a record"
            entry["note"] = f"1 {story['type']} story · {teller}"
        entries.append(entry)

    # births and events in the same year: keep births first
    return sorted(entries, key=lambda e: (e["year"], "url_person" not in e))


# ---------- Map ----------

def places():
    result = []
    for place_id, place in PLACES.items():
        if place["family"] not in VIEWER_FAMILIES:
            continue
        count = len([s for s in all_stories() if s.get("place") == place_id])
        result.append(dict(place, id=place_id, story_count=count))
    return result


def journeys():
    return [dict(j, story=get_story(j["story"]) if j["story"] and can_see_story(j["story"]) else None)
            for j in JOURNEYS if j["family"] in VIEWER_FAMILIES]


def map_summary():
    trips = journeys()
    return {"homelands": len(places()), "journeys": len(trips), "miles": JOURNEY_MILES if trips else 0}


# ---------- Members and invites ----------

def _ago(when):
    """'just now', 'yesterday', '3 days ago', 'last week'..."""
    days = (datetime.now(timezone.utc) - when).days
    if days < 1:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 14:
        return "last week"
    return f"{days // 7} weeks ago"


def members(family_id):
    result = []
    for member in [m for m in MEMBERS if m["family"] == family_id]:
        person = get_person(member["person"])
        word, _ = relation(VIEWER_ID, person["id"])
        told = stories_told_by(person["id"])
        if member["role"] == "pending" and member.get("invited_at"):
            inviter = member.get("invited_by")
            by = "you" if inviter == VIEWER_ID else (PEOPLE[inviter]["first"] if inviter in PEOPLE else None)
            detail = f"invited {_ago(member['invited_at'])}" + (f" by {by}" if by else "")
        elif member.get("note"):
            detail = member["note"]
        else:
            detail = f"{len(told)} {'story' if len(told) == 1 else 'stories'}"
        result.append({
            "person": person,
            "role": member["role"],
            "relation": "You" if word == "you" else word.capitalize(),
            "detail": detail,
            "invited_by": member.get("invited_by"),
        })
    return result


def invite(family_id):
    """What the join page shows once an invite code is found."""
    family = FAMILIES[family_id]
    keeper = next((m["person"] for m in MEMBERS
                   if m["family"] == family_id and m["role"] == "keeper"), None)
    tree = family_tree(family_id)
    return {
        "family": family,
        "inviter": get_person(keeper) if keeper else None,
        "people_count": tree["people_count"],
        "story_count": tree["story_count"],
    }


# ---------- Archive ----------

def archive_items():
    return [dict(record, id=rid) for rid, record in RECORDS.items()
            if record["family"] in VIEWER_FAMILIES]


def archive_counts():
    counts = {}
    for record in archive_items():
        counts[record["kind"]] = counts.get(record["kind"], 0) + 1
    return counts


def can_see_record(record_id):
    record = RECORDS.get(record_id)
    return bool(record) and record["family"] in VIEWER_FAMILIES


def get_record(record_id):
    """A record with the stories that draw on it and its neighbours in the shoebox."""
    if not can_see_record(record_id):
        return None
    items = archive_items()
    position = next(i for i, item in enumerate(items) if item["id"] == record_id)
    return {
        "record": items[position],
        "stories": [s for s in all_stories() if record_id in [r["id"] for r in s["records"]]],
        "previous": items[position - 1] if len(items) > 1 else None,
        "next": items[(position + 1) % len(items)] if len(items) > 1 else None,
    }


def waiting_record():
    used = {r["id"] for s in all_stories() for r in s["records"]}
    for record in archive_items():
        if record.get("waiting") and record["id"] not in used:
            return record
    return None


# ---------- Recorder ----------

def storyteller_options():
    """Living relatives who could be recorded, closest first, then 'me'."""
    options = []
    for pid in PEOPLE:
        if pid == VIEWER_ID or not can_see(pid) or "died" in PEOPLE[pid]:
            continue
        person = get_person(pid)
        word, _ = relation(VIEWER_ID, pid)
        options.append({"person": person, "relation": word})
    order = ["grandfather", "grandmother", "father", "mother", "aunt", "uncle"]
    options.sort(key=lambda o: order.index(o["relation"]) if o["relation"] in order else len(order))
    return options


def questions():
    return QUESTIONS
