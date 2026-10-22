"""Update the installed source checkout without changing private settings."""
import subprocess
from pathlib import Path


def update(root):
    root = Path(root).resolve()
    command = ["git", "-C", str(root)]

    def read(*args):
        return subprocess.run(command + list(args), capture_output=True, text=True, check=True).stdout.strip()

    # A copied source directory must not accidentally update a containing repository.
    if Path(read("rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("Update requires the original Git checkout; clone the repository and install from it")
    if read("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Checkout has local changes or untracked files. Commit, stash, or move them before updating: " + str(root))
    branch = subprocess.run(command + ["symbolic-ref", "--quiet", "--short", "HEAD"],
                            capture_output=True, text=True)
    if branch.returncode:
        raise ValueError("Checkout has a detached HEAD. Switch to a branch with an upstream before updating")
    upstream = subprocess.run(command + ["rev-parse", "--abbrev-ref", "@{upstream}"],
                              capture_output=True, text=True)
    if upstream.returncode:
        raise ValueError("Branch has no upstream. Configure its Git upstream before updating")
    print("Updating " + str(root) + " from " + upstream.stdout.strip(), flush=True)
    subprocess.run(command + ["pull", "--no-rebase", "--ff-only"], check=True)
    print("Source is up to date. Launcher links use this checkout immediately.")
    print("Existing sessions keep their arrangement; updated layouts apply to new sessions.")
    print("To validate and refresh installation integrations, run from this checkout: ./install.sh --no-dependencies")
    return 0
