# Branch Spoken

A place for families to keep the stories they tell about each other. Join your family tree, click on a relative, and read the memories other family members have shared about them.

## Planned features

- **Family tree**: see everyone in your family and open any relative's page.
- **Relative profiles**: every story written about a person, in one place.
- **Add a memory**: write a story once and tag everyone it's about. A story about fixing a lawn mower with Grandpa shows up on both Dad's and Grandpa's pages and stays credited to whoever wrote it.
- **More than one family**: a person can belong to two family trees and switch between them, and each story stays with the family it was shared in.

## Stack

1. HTML, CSS and JavaScript front end
2. Flask
3. PostgreSQL (in progress)

## Project structure

```
branchspoken/
├── app.py                # Flask app and page routes
├── db.py                 # PostgreSQL connection, loads the family for each request
├── accounts.py           # Sign up, sign in and joining a tree
├── memories.py           # Saves new stories and checks uploaded recordings and photos
├── invites.py            # Inviting relatives and cancelling invites
├── uploads/              # Recordings and photos families add (not in git)
├── data.py               # Sample family that seed.py loads into the database
├── family.py             # Relationships, story counts and page data
├── schema.sql            # PostgreSQL tables
├── seed.py               # Creates the tables and loads the sample family
├── .env.example          # Database settings to copy into .env
├── requirements.txt
├── static/
│   ├── css/
│   │   └── style.css     # Styles shared by every page
│   └── js/
│       ├── tree.js       # Switch between family trees
│       ├── filters.js    # Filter and search stories and the archive
│       ├── invite.js     # Copy the invite link
│       ├── share.js      # Share a relative's page
│       ├── story.js      # Follow the transcript while a story plays
│       └── recorder.js   # Record, time and transcribe interviews
├── templates/
│   ├── base.html         # Page layout every template extends
│   ├── partials/
│   │   ├── tabbar.html   # Bottom navigation
│   │   └── stories.html  # Story rows and bylines used on several pages
│   ├── index.html        # Welcome page
│   ├── login.html        # Sign in
│   ├── signup.html       # Create an account and a new family tree
│   ├── join.html         # Join a family tree from an invite
│   ├── tree.html         # Family tree home page
│   ├── relative.html     # A relative's profile and their stories
│   ├── story.html        # Read or listen to a single story
│   ├── add-memory.html   # Record a relative with guided interview questions
│   ├── timeline.html     # Both sides of the family on one timeline
│   ├── map.html          # Where the family comes from
│   ├── family.html       # Invite relatives and see who is in the tree
│   ├── archive.html      # The shoebox: old photos, records and letters
│   └── stories.html      # Every story, with search and filters
└── README.md
```

## Pages

| URL | Page |
| --- | --- |
| `/` | Welcome |
| `/login` | Sign in |
| `/signup` | Plant a new tree |
| `/join` | Join a tree from an invite |
| `/tree` | Family tree |
| `/relatives/<id>` | A relative's profile |
| `/stories` | All stories |
| `/stories/<id>` | One story |
| `/add-memory` | Record a memory |
| `/timeline` | Timeline |
| `/map` | Map |
| `/family` | Members and invites |
| `/archive` | The shoebox |

## Run it

Needs Python 3 and PostgreSQL 17.

### 1. Install PostgreSQL

On Windows, from an administrator terminal:

```
winget install --id PostgreSQL.PostgreSQL.17 --exact
```

Remember the password you choose for the `postgres` user during setup.

### 2. Create the database

```
psql -U postgres -c "CREATE USER branchspoken WITH PASSWORD 'branchspoken';"
psql -U postgres -c "CREATE DATABASE branchspoken OWNER branchspoken;"
```

If `psql` isn't found, it's in `C:\Program Files\PostgreSQL\17\bin`.

### 3. Set up the app

```
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # macOS/Linux: cp .env.example .env
python seed.py
flask --app app run --debug
```

Then open http://127.0.0.1:5000.

Running `python seed.py` again resets the database to the sample family.

### Demo accounts

`python seed.py` creates two accounts in the sample family, both with the password `family-stories`:

- `daniel@example.com`: Daniel, who belongs to both the Miller and Sullivan trees
- `thomas@example.com`: Thomas, Daniel's father, who started the Miller tree

To try joining, sign up through **I was invited by family** with the code `MILLER-K7QF-29XD` and the name Claire Miller. Claire is waiting on a pending invite, so the new account takes over her place in the tree.

## Security

- Passwords are stored as salted hashes, never as plain text.
- You only see people, stories, records and places from the family trees you belong to. Everything else returns "Not found".
- Every form that changes something carries a CSRF token, so other websites can't submit forms as you.
- Signing in, signing up and entering invite codes are rate-limited to stop guessing.
- Invite codes are long and random (`MILLER-K7QF-29XD`). A tree's Keeper can replace the code from the Family page if it gets shared.
- Responses send a Content Security Policy and other security headers, so pages only run this site's own scripts and can't be embedded elsewhere.
- Database queries use parameters, and templates escape everything people type.
- Uploads are capped at 25 MB and must really be audio or images: the file's contents are checked, not just its name.
- Uploaded files get random names, live outside `static/`, and are only served to people who can see the story they belong to.

Before putting the site online:

- Serve it over HTTPS and set `SESSION_COOKIE_SECURE=1` in `.env`.
- Use a long random `SECRET_KEY`.
- Move the rate limiter's storage from memory to Redis, so limits survive restarts and are shared between workers.

