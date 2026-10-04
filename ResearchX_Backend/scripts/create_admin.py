"""Create the first administrator without running the destructive legacy initdb.py.

Run from ResearchX_Backend after the API has initialized/migrated the database:
    python -m scripts.create_admin
"""

import argparse
import getpass
import os
import re
import uuid

from dotenv import load_dotenv

load_dotenv()

from core.backend.db.database import SessionLocal  # noqa: E402
from core.backend.db.models import Team, User  # noqa: E402
from core.backend.router.router_user import _hash_password  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Create the first ResearchX administrator")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--team-name", default="默认团队")
    args = parser.parse_args()
    username = args.username.strip()
    team_name = args.team_name.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,50}", username):
        parser.error("username must contain 3–50 letters, digits, underscores or hyphens")
    if not 1 <= len(team_name) <= 50:
        parser.error("team name must contain 1–50 characters")
    password = os.getenv("RESEARCHX_ADMIN_PASSWORD") or getpass.getpass("Administrator password: ")
    if not 8 <= len(password) <= 128:
        parser.error("password must contain 8–128 characters")

    with SessionLocal() as db:
        if db.query(User).filter(User.username == username).first():
            parser.error(f"user {username!r} already exists; no data was changed")
        if db.query(Team).filter(Team.team_name == team_name).first():
            parser.error(f"team name {team_name!r} already exists; no data was changed")
        lid = uuid.uuid4().hex
        db.add(User(username=username, password=_hash_password(password), lid=lid, role="admin"))
        db.add(Team(team_id=lid, owner_username=username, team_name=team_name))
        db.commit()
    print(f"Created administrator {username!r} and team {team_name!r}")


if __name__ == "__main__":
    main()
