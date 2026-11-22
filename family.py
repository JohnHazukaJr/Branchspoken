"""Works out relationships, story counts and page data from the family data."""

from db import load_family_data

# Who is signed in. Comes from the login session once accounts exist.
VIEWER_ID = "daniel"

# Total distance of the journeys on the map
JOURNEY_MILES = 4600

# Filled in from the database by refresh() at the start of every request
PEOPLE, FAMILIES, STORIES, RECORDS, PLACES = {}, {}, {}, {}, {}
JOURNEYS, EVENTS, MEMBERS, QUESTIONS = [], [], [], []


def refresh():
    """Reload the family from the database so new stories show up right away."""
    globals().update(load_family_data())


# ---------- People ----------

def get_person(person_id):
    """A person with their id and display names filled in, or None."""
    if person_id not in PEOPLE:
        return None
    p = dict(PEOPLE[person_id], id=person_id)
    p["name"] = f"{p['first']} {p['last']}"
    p["pronoun"] = "her" if p["sex"] == "f" else "his"
    p["object"] = "her" if p["sex"] == "f" else "him"
    return p


def parents_of(person_id):
    return PEOPLE[person_id].get("parents", [])


def children_of(*parent_ids):
    """Children whose parents are exactly these people, oldest first."""
    wanted = set(parent_ids)
    kids = [pid for pid, p in PEOPLE.items() if set(p.get("parents", [])) == wanted]
    return sorted(kids, key=lambda pid: PEOPLE[pid]["born"])


def all_children_of(person_id):
    kids = [pid for pid, p in PEOPLE.items() if person_id in p.get("parents", [])]
    return sorted(kids, key=lambda pid: PEOPLE[pid]["born"])


def siblings_of(person_id):
    mine = set(parents_of(person_id))
    if not mine:
        return []
    return [pid for pid, p in PEOPLE.items()
            if pid != person_id and mine & set(p.get("parents", []))]


def spouse_of(person_id):
    return PEOPLE[person_id].get("spouse")


# ---------- Relationships ----------

WORDS = {
    "spouse": ("husband", "wife"),
    "parent": ("father", "mother"),
    "child": ("son", "daughter"),
    "sibling": ("brother", "sister"),
    "grandparent": ("grandfather", "grandmother"),
    "great-grandparent": ("great-grandfather", "great-grandmother"),
    "grandchild": ("grandson", "granddaughter"),
    "aunt-uncle": ("uncle", "aunt"),
    "niece-nephew": ("nephew", "niece"),
    "cousin": ("cousin", "cousin"),
    "parent-in-law": ("father-in-law", "mother-in-law"),
    "child-in-law": ("son-in-law", "daughter-in-law"),
}


def _word(kind, person_id):
    male, female = WORDS[kind]
    return female if PEOPLE[person_id]["sex"] == "f" else male


def _side(parent_id):
    return "mother's side" if PEOPLE[parent_id]["sex"] == "f" else "father's side"


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
        for aunt_or_uncle in siblings_of(parent):
            if to_id in all_children_of(aunt_or_uncle):
                return (_word("cousin", to_id), _side(parent))
        for grandparent in parents_of(parent):
            if to_id in parents_of(grandparent):
                return (_word("great-grandparent", to_id), _side(parent))

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
    """Every story, newest first."""
    ids = sorted(STORIES, key=lambda sid: STORIES[sid]["added"], reverse=True)
    return [get_story(sid) for sid in ids]


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
        family.append((_word("spouse", spouse_of(person_id)).capitalize(), [get_person(spouse_of(person_id))]))
    for label, ids in [("Parents", parents_of(person_id)),
                       ("Brothers and sisters", siblings_of(person_id)),
                       ("Children", all_children_of(person_id)),
                       ("Grandchildren", [g for c in all_children_of(person_id) for g in all_children_of(c)])]:
        if ids:
            family.append((label, [get_person(pid) for pid in ids]))

    # suggest asking a living child (or the husband or wife) for a story
    ask = None
    for pid in all_children_of(person_id) + [spouse_of(person_id)]:
        if pid and pid != VIEWER_ID and "died" not in PEOPLE[pid]:
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
    }


# ---------- Family tree ----------

def _node(person_ids):
    people = [get_person(pid) for pid in person_ids]
    if len(people) == 2:
        years = f"b. {people[0]['born']} · b. {people[1]['born']}"
    else:
        years = f"b. {people[0]['born']}"
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
        p = get_person(pid)
        entries.append({
            "year": p["born"], "side": p["side"], "title": f"{p['first']} is born",
            "url_person": pid,
            "note": "That's you" if pid == VIEWER_ID else p["birthplace"],
        })
    for event in EVENTS:
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
        count = len([s for s in STORIES.values() if s.get("place") == place_id])
        result.append(dict(place, id=place_id, story_count=count))
    return result


def journeys():
    return [dict(j, story=get_story(j["story"]) if j["story"] else None) for j in JOURNEYS]


def map_summary():
    return {"homelands": len(PLACES), "journeys": len(JOURNEYS), "miles": JOURNEY_MILES}


# ---------- Members and invites ----------

def members():
    result = []
    for member in MEMBERS:
        person = get_person(member["person"])
        word, _ = relation(VIEWER_ID, person["id"])
        told = stories_told_by(person["id"])
        if member.get("note"):
            detail = member["note"]
        else:
            detail = f"{len(told)} {'story' if len(told) == 1 else 'stories'}"
        result.append({
            "person": person,
            "role": member["role"],
            "relation": "You" if word == "you" else word.capitalize(),
            "detail": detail,
        })
    return result


def invite(family_id):
    """Who sent the viewer's invite and how they were added."""
    family = FAMILIES[family_id]
    keeper = next(m["person"] for m in MEMBERS if m["role"] == "keeper")
    inviter = get_person(keeper)
    word, _ = relation(keeper, VIEWER_ID)
    tree = family_tree(family_id)
    return {
        "family": family,
        "inviter": inviter,
        "added_as": f"{inviter['first']}'s {word}",
        "viewer": get_person(VIEWER_ID),
        "people_count": tree["people_count"],
        "story_count": tree["story_count"],
    }


# ---------- Archive ----------

def archive_items():
    return [dict(record, id=rid) for rid, record in RECORDS.items()]


def archive_counts():
    counts = {}
    for record in RECORDS.values():
        counts[record["kind"]] = counts.get(record["kind"], 0) + 1
    return counts


def waiting_record():
    for rid, record in RECORDS.items():
        if record.get("waiting"):
            return dict(record, id=rid)
    return None


# ---------- Recorder ----------

def storyteller_options():
    """Living relatives who could be recorded, closest first, then 'me'."""
    options = []
    for pid in PEOPLE:
        if pid == VIEWER_ID or "died" in PEOPLE[pid]:
            continue
        person = get_person(pid)
        word, _ = relation(VIEWER_ID, pid)
        options.append({"person": person, "relation": word})
    order = ["grandfather", "grandmother", "father", "mother", "aunt", "uncle"]
    options.sort(key=lambda o: order.index(o["relation"]) if o["relation"] in order else len(order))
    return options


def questions():
    return QUESTIONS
