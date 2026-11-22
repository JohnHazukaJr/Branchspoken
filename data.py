"""Sample family data.

seed.py loads this into PostgreSQL. The app itself reads from the database.
"""


# ---------- People ----------
# side: which family line they belong to ("miller", "sullivan" or "both")

PEOPLE = {
    "walter": {
        "first": "Walter", "last": "Miller", "sex": "m", "side": "miller",
        "born": 1927, "birthplace": "Minneapolis, Minnesota",
        "parents": [], "spouse": "ruth",
    },
    "ruth": {
        "first": "Ruth", "last": "Miller", "sex": "f", "side": "miller",
        "born": 1931, "birthplace": "Springfield, Illinois",
        "died": 2019, "deathplace": "Minneapolis, Minnesota",
        "parents": [], "spouse": "walter",
        "photo": "images/ruth.jpg", "photo_caption": "Ruth, c. 1950",
    },
    "carol": {
        "first": "Carol", "last": "Lund", "sex": "f", "side": "miller",
        "born": 1955, "birthplace": "Minneapolis, Minnesota",
        "parents": ["walter", "ruth"],
    },
    "emily": {
        "first": "Emily", "last": "Lund", "sex": "f", "side": "miller",
        "born": 1984, "birthplace": "Minneapolis, Minnesota",
        "parents": ["carol"],
    },
    "thomas": {
        "first": "Thomas", "last": "Miller", "sex": "m", "side": "miller",
        "born": 1958, "birthplace": "Minneapolis, Minnesota",
        "parents": ["walter", "ruth"], "spouse": "anne",
    },
    "henry": {
        "first": "Henry", "last": "Sullivan", "sex": "m", "side": "sullivan",
        "born": 1932, "birthplace": "Boston, Massachusetts",
        "parents": [], "spouse": "margaret",
    },
    "margaret": {
        "first": "Margaret", "last": "Sullivan", "sex": "f", "side": "sullivan",
        "born": 1936, "birthplace": "Boston, Massachusetts",
        "parents": [], "spouse": "henry",
    },
    "anne": {
        "first": "Anne", "last": "Miller", "sex": "f", "side": "sullivan",
        "born": 1961, "birthplace": "Boston, Massachusetts",
        "parents": ["henry", "margaret"], "spouse": "thomas",
    },
    "patrick": {
        "first": "Patrick", "last": "Sullivan", "sex": "m", "side": "sullivan",
        "born": 1964, "birthplace": "Boston, Massachusetts",
        "parents": ["henry", "margaret"],
    },
    "sean": {
        "first": "Sean", "last": "Sullivan", "sex": "m", "side": "sullivan",
        "born": 1992, "birthplace": "Minneapolis, Minnesota",
        "parents": ["patrick"],
    },
    "daniel": {
        "first": "Daniel", "last": "Miller", "sex": "m", "side": "both",
        "born": 1996, "birthplace": "Minneapolis, Minnesota",
        "parents": ["thomas", "anne"],
    },
    "claire": {
        "first": "Claire", "last": "Miller", "sex": "f", "side": "both",
        "born": 1999, "birthplace": "Minneapolis, Minnesota",
        "parents": ["thomas", "anne"],
    },
}


# ---------- Family trees ----------
# A person can belong to more than one tree.

FAMILIES = {
    "miller": {
        "name": "The Miller Family",
        "branches": [
            {"side": "miller", "title": "The Millers", "root": "walter"},
            {"side": "sullivan", "title": "The Sullivans", "root": "henry"},
        ],
        # the couple where the two lines join
        "meet": ["thomas", "anne"], "married": 1994,
        "invite_code": "MILLER-4821",
    },
    "sullivan": {
        "name": "The Sullivan Family",
        "branches": [
            {"side": "sullivan", "title": "The Sullivans", "root": "henry"},
        ],
        "meet": ["thomas", "anne"], "married": 1994,
        "invite_code": "SULLIVAN-1167",
    },
}


# ---------- Stories ----------
# type: voice, photo, record or text
# subjects: who the story is about, first one is the main person
# Transcript paragraphs can link a detail to a record with [words](record-id)

STORIES = {
    "moms-kitchen-song": {
        "title": "Mom's kitchen song", "type": "voice",
        "teller": "henry", "subjects": ["henry"],
        "era": "1940s", "year": 1945, "minutes": 3, "place": "boston",
        "added": "2026-11-20",
        "excerpt": "Oh, it was always \"Down by the Salley Gardens.\"",
        "body": [
            "Oh, it was always \"Down by the Salley Gardens.\" Her mother brought it over from County Clare.",
            "She'd sing it peeling potatoes, and if you came in the kitchen she'd stop, like you'd caught her at something.",
            "My sister Nora learned every word just by sitting on the back steps and listening.",
        ],
    },
    "ruths-first-winter": {
        "title": "Ruth's first winter up north", "type": "voice",
        "teller": "carol", "subjects": ["ruth", "walter"],
        "era": "Winter 1952", "year": 1952, "minutes": 4, "place": "minneapolis",
        "added": "2026-11-18",
        "photo": "images/train-ticket.jpg",
        "photo_alt": "A worn train ticket from Chicago to Minneapolis",
        "photo_caption": "Train ticket, Chicago to Minneapolis",
        "audio": "audio/ruths-first-winter.mp3", "audio_length": "4 min 10 sec",
        "records": ["ruth-ticket", "ruth-directory"],
        "records_note": "The train name and date come from her ticket stub, and the address comes from the 1952 Minneapolis city directory.",
        "excerpt": "She had one wool coat and swore she would never get used to the snow.",
        "body": [
            "Mom always said she got on the train in Chicago wearing the only wool coat she owned. "
            "It was the [Twin Zephyr](ruth-ticket), and it left on [January 14, 1952](ruth-ticket). "
            "She was twenty years old and had never seen snow that stayed on the ground for more than a day.",
            "Dad met her at the station with a pair of his sister's boots because he knew she wouldn't have any. "
            "She said they were two sizes too big and she wore them all winter anyway.",
            "They rented a room on [Lyndale Avenue](ruth-directory) above a bakery, and she used to say the only "
            "reason she survived February was the warm floor and the smell of bread coming up through it.",
            "She swore she would never get used to the cold. She lived in Minnesota for sixty-seven more years "
            "and never did.",
        ],
    },
    "leaving-boston": {
        "title": "Leaving Boston", "type": "voice",
        "teller": "margaret", "subjects": ["margaret", "henry", "anne"],
        "era": "1967", "year": 1967, "minutes": 7, "place": "boston",
        "added": "2026-11-16",
        "excerpt": "We packed the station wagon the night before so we could leave before the sun came up.",
        "body": [
            "We packed the station wagon the night before so we could leave before the sun came up.",
            "Henry had the job offer in Minneapolis in his shirt pocket the whole drive, like it might blow away.",
            "Anne cried until Ohio, and then she fell asleep on the cooler and didn't wake up until Chicago.",
        ],
    },
    "lawn-mower": {
        "title": "Fixing the lawn mower", "type": "text",
        "teller": "thomas", "subjects": ["thomas", "walter"],
        "era": "Summer 1971", "year": 1971, "place": "minneapolis",
        "added": "2026-11-15",
        "excerpt": "Dad spent a whole Saturday showing me how to clean the carburetor, and we still had to push it back to the garage.",
        "body": [
            "Dad spent a whole Saturday showing me how to clean the carburetor, and we still had to push it back to the garage.",
            "He never got mad about it. He just said, \"Well, now you know what the inside looks like,\" and went in for lunch.",
        ],
    },
    "sunday-pot-roast": {
        "title": "Sunday pot roast", "type": "photo",
        "teller": "emily", "subjects": ["ruth"],
        "era": "1960s", "year": 1960, "detail": "photo and recipe card", "place": "minneapolis",
        "added": "2026-11-14",
        "records": ["pot-roast-card"],
        "excerpt": "Grandma's card says \"cook until done,\" which was not helpful.",
        "body": [
            "Grandma's card says \"cook until done,\" which was not helpful.",
            "Mom figured out the rest by watching her every Sunday for twenty years.",
        ],
    },
    "letters-from-korea": {
        "title": "Letters from Korea", "type": "text",
        "teller": "thomas", "subjects": ["ruth", "walter"],
        "era": "1951", "year": 1951,
        "added": "2026-11-12",
        "records": ["letter-from-korea"],
        "excerpt": "Dad wrote to her every week, and she kept every one in a coffee can.",
        "body": [
            "Dad wrote to her every week, and she kept every one in a coffee can.",
            "Most of them are about the weather and the food. The last one just says he's coming home, and to buy boots.",
        ],
    },
    "the-lake-cabin": {
        "title": "The lake cabin", "type": "photo",
        "teller": "carol", "subjects": ["ruth", "walter", "carol", "thomas"],
        "era": "c. 1965", "year": 1965, "detail": "12 photos",
        "added": "2026-11-10",
        "records": ["lake-cabin"],
        "excerpt": "Every August, two weeks, no telephone.",
        "body": ["Every August, two weeks, no telephone. Mom read on the dock and Dad fished and never caught anything."],
    },
    "the-church-choir": {
        "title": "The church choir", "type": "voice",
        "teller": "walter", "subjects": ["ruth"],
        "era": "1950s", "year": 1953, "minutes": 6, "place": "minneapolis",
        "added": "2026-11-08",
        "excerpt": "She could hold a note longer than anybody in that church.",
        "body": ["She could hold a note longer than anybody in that church, and she knew it."],
    },
    "born-in-springfield": {
        "title": "Born in Springfield", "type": "record",
        "teller": None, "subjects": ["ruth"],
        "era": "1931", "year": 1931, "place": "springfield",
        "added": "2026-11-05",
        "records": ["ruth-birth"],
        "excerpt": "Ruth was born at home on Cook Street, the second of four children.",
        "body": ["Ruth was born at home on Cook Street, the second of four children."],
    },
    "st-brigids": {
        "title": "The wedding at St. Brigid's", "type": "photo",
        "teller": "margaret", "subjects": ["henry", "margaret"],
        "era": "June 1958", "year": 1958, "detail": "8 photos", "place": "boston",
        "added": "2026-11-03",
        "records": ["sullivan-wedding"],
        "excerpt": "It rained all morning and stopped right as we came down the steps.",
        "body": ["It rained all morning and stopped right as we came down the steps."],
    },
    "night-shift": {
        "title": "My first night shift", "type": "voice",
        "teller": "anne", "subjects": ["anne"],
        "era": "1983", "year": 1983, "minutes": 5, "place": "minneapolis",
        "added": "2026-10-30",
        "excerpt": "Nobody tells you how quiet a hospital gets at three in the morning.",
        "body": ["Nobody tells you how quiet a hospital gets at three in the morning."],
    },
    "paper-route": {
        "title": "The paper route", "type": "text",
        "teller": "patrick", "subjects": ["patrick"],
        "era": "1976", "year": 1976, "place": "minneapolis",
        "added": "2026-10-25",
        "excerpt": "Ninety-one houses, and the Hendersons' dog hated me personally.",
        "body": ["Ninety-one houses, and the Hendersons' dog hated me personally."],
    },
}


# ---------- Records, photos and letters (the shoebox) ----------
# kind: photo, record, letter or document

RECORDS = {
    "ruth-ticket": {
        "title": "Train ticket", "kind": "record", "year": "1952", "people": "Ruth",
        "image": "images/archive/train-ticket.jpg",
        "alt": "Train ticket from Chicago to Minneapolis",
    },
    "sullivan-wedding": {
        "title": "Wedding, St. Brigid's", "kind": "photo", "year": "1958", "people": "Henry & Margaret",
        "image": "images/archive/sullivan-wedding.jpg",
        "alt": "Henry and Margaret on the church steps on their wedding day",
    },
    "letter-from-korea": {
        "title": "Letter to Ruth", "kind": "letter", "year": "1951", "people": "3 pages",
        "image": "images/archive/letter-from-korea.jpg",
        "alt": "Handwritten letter from Walter to Ruth",
    },
    "lake-cabin": {
        "title": "The lake cabin", "kind": "photo", "year": "c. 1965", "people": "3 people tagged",
        "image": "images/archive/lake-cabin.jpg",
        "alt": "The Miller family on the dock at the lake cabin",
    },
    "ruth-birth": {
        "title": "Birth record", "kind": "record", "year": "1931", "people": "Ruth",
        "image": "images/archive/ruth-birth-record.jpg",
        "alt": "Ruth's birth record from Springfield, Illinois",
    },
    "pot-roast-card": {
        "title": "Pot roast recipe card", "kind": "document", "year": "c. 1960", "people": "Ruth",
        "image": "images/archive/pot-roast-card.jpg",
        "alt": "Handwritten recipe card for Sunday pot roast",
    },
    "ruth-directory": {
        "title": "City directory", "kind": "record", "year": "1952", "people": "Ruth & Walter",
        "image": "images/archive/city-directory.jpg",
        "alt": "Page from the 1952 Minneapolis city directory",
    },
    "passenger-list-1909": {
        "title": "Passenger list", "kind": "record", "year": "1909", "people": "Bridget Keane",
        "image": "images/archive/passenger-list.jpg",
        "alt": "Ship passenger list from 1909, Queenstown to Boston",
        "waiting": "Bridget's 1909 passenger list has 5 details we can narrate.",
    },
}


# ---------- Places and journeys (the map) ----------
# x and y place the pin on the map, in percent

PLACES = {
    "county-clare": {
        "name": "County Clare, Ireland", "short": "County Clare", "side": "sullivan",
        "families": "Sullivan & Keane", "years": "1880s–1909", "x": 84, "y": 28,
    },
    "boston": {
        "name": "Boston, Massachusetts", "short": "Boston", "side": "sullivan",
        "families": "Sullivan & Keane", "years": "1909–1967", "x": 46, "y": 45,
    },
    "springfield": {
        "name": "Springfield, Illinois", "short": "Springfield", "side": "miller",
        "families": "Ruth's family", "years": "1931–1952", "x": 28, "y": 64,
    },
    "minneapolis": {
        "name": "Minneapolis, Minnesota", "short": "Minneapolis", "side": "both",
        "families": "Where the branches met", "years": None, "x": 20, "y": 42,
    },
}

JOURNEYS = [
    {"year": 1909, "from": "county-clare", "to": "boston", "side": "sullivan",
     "text": "Henry's grandmother sails from County Clare to Boston", "story": None,
     "path": "M84 28 Q66 12 46 45"},
    {"year": 1952, "from": "springfield", "to": "minneapolis", "side": "miller",
     "text": "Ruth takes the train north to Minneapolis", "story": "ruths-first-winter",
     "path": "M28 64 Q16 55 20 42"},
    {"year": 1967, "from": "boston", "to": "minneapolis", "side": "sullivan",
     "text": "The Sullivans drive west from Boston", "story": "leaving-boston",
     "path": "M46 45 Q33 30 20 42"},
]



# ---------- Timeline events besides births ----------

EVENTS = [
    {"year": 1952, "title": "Ruth moves up north", "side": "miller", "story": "ruths-first-winter"},
    {"year": 1967, "title": "The family leaves Boston", "side": "sullivan", "story": "leaving-boston"},
    {"year": 1971, "title": "Fixing the lawn mower", "side": "miller", "story": "lawn-mower"},
    {"year": 1994, "title": "Thomas and Anne get married", "side": "both", "note": "Where the branches meet",
     "anchor": "married-1994"},
]


# ---------- Members of the Miller Family tree ----------
# role: keeper, editor, storyteller or pending

MEMBERS = [
    {"person": "thomas", "role": "keeper", "note": "started the tree"},
    {"person": "anne", "role": "editor", "note": "tends the Sullivan branch"},
    {"person": "henry", "role": "storyteller"},
    {"person": "margaret", "role": "storyteller"},
    {"person": "carol", "role": "storyteller"},
    {"person": "emily", "role": "editor", "note": "tends the Miller branch"},
    {"person": "daniel", "role": "storyteller"},
    {"person": "claire", "role": "pending", "note": "invited 2 days ago"},
    {"person": "patrick", "role": "pending", "note": "invited last week"},
]


# ---------- Interview questions for the recorder ----------

QUESTIONS = [
    "Where did you grow up?",
    "What did your house smell like on a Sunday?",
    "What song did your mother sing while she cooked?",
    "Who was your best friend when you were ten?",
    "What was your first job, and what did it pay?",
    "How did you meet the person you married?",
    "What's something your parents never knew about you?",
    "What do you want your great-grandchildren to know?",
]
