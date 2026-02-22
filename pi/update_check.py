"""
DogPhone update from GitHub. Run git pull in the repo.
Repo: https://github.com/TimothyFsr/Dogphone
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REMOTE = "origin"
BRANCH = "main"


def run_update() -> tuple[bool, str]:
    """Run git pull. Returns (success, message)."""
    if not (REPO_ROOT / ".git").exists():
        return False, "Not a git repo (install from GitHub clone to enable updates)."
    try:
        r = subprocess.run(
            ["git", "pull", REMOTE, BRANCH],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode != 0:
            return False, (r.stderr or r.stdout or "git pull failed").strip()[:500]
        out = (r.stdout or "").strip()
        updated = "Already up to date" not in out
        return True, "Updated." if updated else "Already up to date."
    except subprocess.TimeoutExpired:
        return False, "Update timed out."
    except FileNotFoundError:
        return False, "git not installed."
    except Exception as e:
        return False, str(e)[:500]
