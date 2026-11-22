import re

from flask import Flask, abort, redirect, render_template, request, url_for
from markupsafe import Markup, escape

import db
import family as fam

app = Flask(__name__)
db.init_app(app)

DEFAULT_FAMILY = "miller"


@app.before_request
def load_family():
    # static files don't need the family
    if request.endpoint != "static":
        fam.refresh()


@app.template_filter("record_links")
def record_links(text):
    """Turn [words](record-id) in a transcript into a highlighted link to the record."""
    def link(match):
        return f'<a href="/records/{match.group(2)}"><mark>{match.group(1)}</mark></a>'
    return Markup(re.sub(r"\[([^\]]+)\]\(([\w-]+)\)", link, str(escape(text))))


# ---------- Welcome and accounts ----------

@app.route("/")
def welcome():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # accounts come with the database, for now go straight to the tree
        return redirect(url_for("tree"))
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        return redirect(url_for("tree"))
    return render_template("signup.html")


@app.route("/join", methods=["GET", "POST"])
def join():
    if request.method == "POST":
        return redirect(url_for("tree"))
    return render_template("join.html", invite=fam.invite(DEFAULT_FAMILY))


# ---------- The family ----------

@app.route("/tree")
def tree():
    family_id = request.args.get("family", DEFAULT_FAMILY)
    family_tree = fam.family_tree(family_id)
    if not family_tree:
        abort(404)
    return render_template("tree.html", tree=family_tree, families=fam.FAMILIES)


@app.route("/relatives/<person_id>")
def relative(person_id):
    profile = fam.profile(person_id)
    if not profile:
        abort(404)
    return render_template("relative.html", **profile)


@app.route("/family", methods=["GET", "POST"])
def family():
    if request.method == "POST":
        # sending invites comes later
        return redirect(url_for("family"))
    return render_template("family.html", members=fam.members(),
                           invite_code=fam.FAMILIES[DEFAULT_FAMILY]["invite_code"])


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
    current = fam.get_story(story_id)
    if not current:
        abort(404)

    # step through the other stories about the same person
    siblings = fam.stories_about(current["main"]["id"])
    position = next(i for i, s in enumerate(siblings) if s["id"] == story_id)
    previous_story = siblings[position - 1] if len(siblings) > 1 else None
    next_story = siblings[(position + 1) % len(siblings)] if len(siblings) > 1 else None

    return render_template("story.html", story=current, position=position + 1,
                           count=len(siblings), previous_story=previous_story,
                           next_story=next_story)


@app.route("/add-memory", methods=["GET", "POST"])
def add_memory():
    if request.method == "POST":
        # saving stories comes with the database
        return redirect(url_for("stories"))

    options = fam.storyteller_options()
    chosen = request.args.get("ask") or options[0]["person"]["id"]
    about = request.args.getlist("about") or [chosen]
    return render_template("add-memory.html", options=options, chosen=chosen,
                           about=about, people=[fam.get_person(pid) for pid in fam.PEOPLE],
                           questions=fam.questions())


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
