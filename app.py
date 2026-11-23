import os
import re
from datetime import timedelta

from flask import (Flask, abort, g, redirect, render_template, request,
                   send_from_directory, session, url_for)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFError, CSRFProtect
from markupsafe import Markup, escape

import accounts
import db
import family as fam
import invites
import memories

REQUIRED_SETTINGS = ["SECRET_KEY", "DATABASE_URL"]
missing = [name for name in REQUIRED_SETTINGS if not os.environ.get(name)]
if missing:
    raise RuntimeError(
        f"Missing setting(s): {', '.join(missing)}. Locally, copy .env.example to .env. "
        "On a host like Render, add them as environment variables.")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ["SECRET_KEY"],
    SESSION_COOKIE_HTTPONLY=True,                    # scripts can't read the login cookie
    SESSION_COOKIE_SAMESITE="Lax",
    # only send the login cookie over HTTPS once the site is online
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "").strip().lower() in ("1", "true", "yes"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),   # "Keep me signed in"
    MAX_CONTENT_LENGTH=25 * 1024 * 1024,             # biggest upload: 25 MB
)
db.init_app(app)

# every form that changes something has to carry a token from our own pages
csrf = CSRFProtect(app)

# slow down anyone guessing passwords or invite codes
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")


# ---------- Security headers ----------

CONTENT_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'",   # map pins set their spot inline
    "font-src https://fonts.gstatic.com",
    "img-src 'self' data:",
    "media-src 'self' blob:",
    "connect-src 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "object-src 'none'",
])


@app.after_request
def security_headers(response):
    response.headers["Content-Security-Policy"] = CONTENT_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"
    if g.get("viewer"):
        # family pages shouldn't be kept in shared caches
        response.headers["Cache-Control"] = "private, no-store"
    return response


# ---------- Error pages ----------

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", title="Not found",
                           message="We couldn't find that page, or it belongs to a family you're not part of."), 404


@app.errorhandler(429)
def too_many_tries(error):
    return render_template("error.html", title="Too many tries",
                           message="Please wait a few minutes before trying again."), 429


@app.errorhandler(CSRFError)
def form_expired(error):
    return render_template("error.html", title="That form expired",
                           message="Go back, refresh the page and try again."), 400


@app.errorhandler(413)
def too_big(error):
    return render_template("error.html", title="That file is too big",
                           message="Files can be up to 25 MB."), 413

# pages you can see without signing in
PUBLIC_PAGES = {"welcome", "login", "signup", "join", "static"}


# ---------- Signing in ----------

def sign_in(user_id, person_id, family_id, remember=False):
    session.clear()
    session.permanent = remember
    session["user_id"] = user_id
    session["person_id"] = person_id
    session["family_id"] = family_id


def safe_next(target):
    """Only send people back to a page on this site after signing in."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("tree")


@app.before_request
def load_viewer():
    if request.endpoint == "static":
        return None

    fam.refresh(session.get("person_id"))

    # the database was reset or the person was removed
    if session.get("person_id") and session["person_id"] not in fam.PEOPLE:
        session.clear()
        fam.refresh(None)

    g.viewer = fam.get_person(session["person_id"]) if "person_id" in session else None
    g.families = accounts.families_of(session["person_id"]) if g.viewer else []

    if g.viewer is None and request.endpoint not in PUBLIC_PAGES:
        return redirect(url_for("login", next=request.full_path.rstrip("?")))
    return None


def current_family():
    """The tree being looked at, as long as the viewer belongs to it."""
    family_id = session.get("family_id")
    if family_id not in g.families:
        family_id = g.families[0] if g.families else None
        session["family_id"] = family_id
    return family_id


@app.template_filter("media_url")
def media_url(path):
    """Family uploads go through /media so they stay private, the rest is static."""
    if path.startswith("uploads/"):
        return url_for("media", filename=path.removeprefix("uploads/"))
    return url_for("static", filename=path)


@app.template_filter("record_links")
def record_links(text):
    """Turn [words](record-id) in a transcript into a highlighted link to the record."""
    def link(match):
        return f'<a href="/records/{match.group(2)}"><mark>{match.group(1)}</mark></a>'
    return Markup(re.sub(r"\[([^\]]+)\]\(([\w-]+)\)", link, str(escape(text))))


# ---------- Welcome and accounts ----------

@app.route("/")
def welcome():
    if g.viewer:
        return redirect(url_for("tree"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute; 50 per hour", methods=["POST"])
def login():
    if g.viewer:
        return redirect(url_for("tree"))

    error = None
    if request.method == "POST":
        user = accounts.check_login(request.form["email"], request.form["password"])
        if user:
            families = accounts.families_of(user["person_id"])
            sign_in(user["id"], user["person_id"], families[0] if families else None,
                    remember="remember" in request.form)
            return redirect(safe_next(request.form.get("next")))
        error = "That email and password don't match. Try again."

    return render_template("login.html", error=error, form=request.form,
                           next=request.values.get("next", ""))


@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def signup():
    if g.viewer:
        return redirect(url_for("tree"))

    error = None
    if request.method == "POST":
        form = request.form
        born = int(form["birth_year"]) if form.get("birth_year", "").isdigit() else None
        try:
            user_id, person_id, family_id = accounts.sign_up(
                form["first_name"], form["last_name"], born,
                form["email"], form["password"], form["tree_name"])
        except accounts.AccountError as problem:
            error = str(problem)
        else:
            sign_in(user_id, person_id, family_id)
            return redirect(url_for("tree"))

    return render_template("signup.html", error=error, form=request.form)


@app.route("/join", methods=["GET", "POST"])
@limiter.limit("20 per hour", exempt_when=lambda: not request.values.get("code"))
def join():
    error = None
    code = request.values.get("code", "").strip()

    if request.method == "POST":
        form = request.form
        try:
            user_id, person_id, family_id = accounts.join(
                code, form["first_name"], form["last_name"], form["email"], form["password"])
        except accounts.AccountError as problem:
            error = str(problem)
        else:
            sign_in(user_id, person_id, family_id)
            return redirect(url_for("tree"))

    invite = None
    if code:
        found = accounts.find_family_by_code(code)
        if found:
            invite = fam.invite(found["id"])
        elif request.method == "GET":
            error = "We couldn't find that invite code. Check it and try again."

    return render_template("join.html", invite=invite, code=code, error=error, form=request.form)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("welcome"))


# ---------- The family ----------

@app.route("/tree")
def tree():
    family_id = request.args.get("family")
    if family_id:
        if family_id not in g.families:
            abort(404)
        session["family_id"] = family_id
    else:
        family_id = current_family()

    if not family_id:
        abort(404)
    family_tree = fam.family_tree(family_id)
    families = {fid: fam.FAMILIES[fid] for fid in g.families}
    return render_template("tree.html", tree=family_tree, families=families)


@app.route("/relatives/<person_id>")
def relative(person_id):
    if not fam.can_see(person_id):
        abort(404)
    profile = fam.profile(person_id)
    return render_template("relative.html", **profile)


@app.route("/family", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"])
def family():
    family_id = current_family()
    error = None

    if request.method == "POST":
        try:
            person_id = invites.create_invite(
                family_id, g.viewer["id"], request.form.get("name", ""),
                request.form.get("relationship", ""), request.form.get("contact", ""))
        except invites.InviteError as problem:
            error = str(problem)
        else:
            # show the invite ready to send
            return redirect(url_for("family", invited=person_id) + "#invite-ready")

    # the invite just sent, only for the person who sent it
    sent = invites.get_invite(family_id, request.args.get("invited", ""), g.viewer["id"])

    return render_template("family.html", members=fam.members(family_id),
                           invite_code=fam.FAMILIES[family_id]["invite_code"],
                           family_name=fam.FAMILIES[family_id]["name"],
                           is_keeper=accounts.role_in(g.viewer["id"], family_id) == "keeper",
                           relationships=invites.RELATIONSHIPS, sent=sent,
                           error=error, form=request.form)


@app.route("/family/invites/<person_id>/cancel", methods=["POST"])
def cancel_invite(person_id):
    family_id = current_family()
    is_keeper = accounts.role_in(g.viewer["id"], family_id) == "keeper"
    if not invites.cancel_invite(family_id, person_id, g.viewer["id"], is_keeper):
        abort(404)
    return redirect(url_for("family"))


@app.route("/family/new-invite-code", methods=["POST"])
def new_invite_code():
    family_id = current_family()
    if accounts.role_in(g.viewer["id"], family_id) != "keeper":
        abort(403)
    accounts.new_invite_code(family_id)
    return redirect(url_for("family"))


# ---------- Stories ----------

@app.route("/stories")
def stories():
    story_list = fam.all_stories()
    place = fam.PLACES.get(request.args.get("place"))
    if place:
        story_list = [s for s in story_list if s.get("place") == request.args["place"]]
    return render_template("stories.html", stories=story_list, place=place,
                           total=len(fam.all_stories()), teller_count=len(fam.storytellers()))


@app.route("/stories/<story_id>")
def story(story_id):
    if not fam.can_see_story(story_id):
        abort(404)
    current = fam.get_story(story_id)

    # step through the other stories about the same person
    siblings = fam.stories_about(current["main"]["id"])
    position = next(i for i, s in enumerate(siblings) if s["id"] == story_id)
    previous_story = siblings[position - 1] if len(siblings) > 1 else None
    next_story = siblings[(position + 1) % len(siblings)] if len(siblings) > 1 else None

    return render_template("story.html", story=current, position=position + 1,
                           count=len(siblings), previous_story=previous_story,
                           next_story=next_story)


@app.route("/add-memory", methods=["GET", "POST"])
@limiter.limit("30 per hour", methods=["POST"])
def add_memory():
    options = fam.storyteller_options()
    option_ids = [o["person"]["id"] for o in options]
    values = request.form if request.method == "POST" else request.args
    error = None

    if request.method == "POST":
        # only people from the viewer's own trees, whatever the form says
        teller = request.form.get("storyteller")
        teller_id = teller if teller in option_ids else g.viewer["id"]
        subjects = [pid for pid in request.form.getlist("about") if fam.can_see(pid)]
        record_id = request.form.get("record")
        record_id = record_id if fam.can_see_record(record_id) else None
        try:
            story_id = memories.save_memory(request.form, request.files, teller_id, subjects, fam.PLACES,
                                            record_id=record_id)
        except memories.StoryError as problem:
            error = str(problem)
        else:
            return redirect(url_for("story", story_id=story_id))

    ask = values.get("ask") or values.get("storyteller")
    if ask not in option_ids and ask != "me":
        ask = None
    chosen = ask or (option_ids[0] if options else "me")
    about = [pid for pid in values.getlist("about") if fam.can_see(pid)]
    if request.method == "GET":
        about = about or [chosen if chosen != "me" else g.viewer["id"]]
    people = [fam.get_person(pid) for pid in fam.PEOPLE if fam.can_see(pid)]
    from_record = values.get("record")
    from_record = fam.RECORDS[from_record] | {"id": from_record} if fam.can_see_record(from_record) else None
    return render_template("add-memory.html", options=options, chosen=chosen,
                           about=about, people=people, questions=fam.questions(),
                           error=error, form=request.form, from_record=from_record)


@app.route("/write", methods=["GET", "POST"])
@limiter.limit("30 per hour", methods=["POST"])
def write():
    """Write a story instead of recording it. The writer is always the signed-in person."""
    values = request.form if request.method == "POST" else request.args
    record_id = values.get("record")
    record_id = record_id if fam.can_see_record(record_id) else None
    error = None

    if request.method == "POST":
        subjects = [pid for pid in request.form.getlist("about") if fam.can_see(pid)]
        form = request.form.to_dict()
        form["transcript"] = request.form.get("story", "")
        try:
            story_id = memories.save_memory(form, request.files, g.viewer["id"], subjects, fam.PLACES,
                                            record_id=record_id)
        except memories.StoryError as problem:
            error = str(problem)
        else:
            return redirect(url_for("story", story_id=story_id))

    about = [pid for pid in values.getlist("about") if fam.can_see(pid)]
    people = [fam.get_person(pid) for pid in fam.PEOPLE if fam.can_see(pid)]
    from_record = fam.RECORDS[record_id] | {"id": record_id} if record_id else None
    return render_template("write.html", people=people, about=about, from_record=from_record,
                           error=error, form=request.form)


@app.route("/records/<record_id>")
def record(record_id):
    found = fam.get_record(record_id)
    if not found:
        abort(404)
    return render_template("record.html", **found)


@app.route("/media/<path:filename>")
def media(filename):
    """A recording or photo, only for people who can see the story it belongs to."""
    if not fam.can_see_media(f"uploads/{filename}"):
        abort(404)
    return send_from_directory(memories.UPLOAD_DIR, filename)


# ---------- Exploring ----------

@app.route("/timeline")
def timeline():
    return render_template("timeline.html", entries=fam.timeline())


@app.route("/map")
def family_map():
    return render_template("map.html", places=fam.places(), journeys=fam.journeys(),
                           summary=fam.map_summary())


@app.route("/archive")
def archive():
    return render_template("archive.html", items=fam.archive_items(),
                           counts=fam.archive_counts(), waiting=fam.waiting_record())


if __name__ == "__main__":
    app.run(debug=True)
