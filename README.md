# Branch Spoken

A place for families to keep the stories they tell about each other. Join your family tree, click on a relative, and read the memories other family members have shared about them.

## Planned features

- **Family tree**: see everyone in your family and open any relative's page.
- **Relative profiles**: every story written about a person, in one place.
- **Add a memory**: write a story once and tag everyone it's about. A story about fixing a lawn mower with Grandpa shows up on both Dad's and Grandpa's pages and stays credited to whoever wrote it.
- **More than one family**: a person can belong to two family trees and switch between them, and each story stays with the family it was shared in.

## Stack

1. HTML, CSS and JavaScript front end (in progress)
2. Flask
3. PostgreSQL

## Project structure

```
branchspoken/
├── index.html    # Welcome page
├── login.html    # Sign in
├── signup.html   # Create an account and a new family tree
├── join.html     # Join a family tree from an invite
├── tree.html     # Family tree home page
├── relative.html # A relative's profile and their stories
├── story.html    # Read or listen to a single story
├── add-memory.html # Record a relative with guided interview questions
└── README.md
```

## Run it

No build step yet. Open `index.html` in a browser.
