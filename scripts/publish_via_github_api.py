from __future__ import annotations

import argparse
import base64
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PUBLISH_PATHS = [
    ".gitignore",
    "README.md",
    "content",
    "docs",
    "prompts",
    "scripts",
    "site",
]


def run_json(args: list[str], payload: dict | None = None) -> dict:
    cmd = ["gh", "api", *args]
    kwargs = {
        "cwd": ROOT,
        "text": True,
        "capture_output": True,
        "check": False,
    }
    if payload is not None:
        cmd.extend(["--input", "-"])
        kwargs["input"] = json.dumps(payload)

    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout or "{}")


def run_text(args: list[str]) -> str:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def infer_repo(explicit_repo: str | None) -> str:
    if explicit_repo:
        return explicit_repo

    remote_url = run_text(["git", "config", "--get", "remote.origin.url"])
    if remote_url.startswith("https://github.com/"):
        repo = remote_url.removeprefix("https://github.com/").removesuffix(".git")
        if "/" in repo:
            return repo
    if remote_url.startswith("git@github.com:"):
        repo = remote_url.removeprefix("git@github.com:").removesuffix(".git")
        if "/" in repo:
            return repo

    raise SystemExit("Could not infer GitHub repo. Pass --repo owner/name.")


def iter_publish_files() -> list[Path]:
    files: list[Path] = []
    for item in PUBLISH_PATHS:
        path = ROOT / item
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and "__pycache__" not in child.parts and child.suffix != ".pyc":
                    files.append(child)
    return sorted(files)


def posix_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def create_blob(repo: str, path: Path) -> str:
    content = base64.b64encode(path.read_bytes()).decode("ascii")
    blob = run_json(
        [f"repos/{repo}/git/blobs", "--method", "POST"],
        {"content": content, "encoding": "base64"},
    )
    return blob["sha"]


def publish(repo: str, branch: str, message: str) -> None:
    ref = run_json([f"repos/{repo}/git/ref/heads/{branch}"])
    parent_sha = ref["object"]["sha"]
    parent_commit = run_json([f"repos/{repo}/git/commits/{parent_sha}"])
    base_tree = parent_commit["tree"]["sha"]

    tree_entries = []
    for path in iter_publish_files():
        blob_sha = create_blob(repo, path)
        tree_entries.append(
            {
                "path": posix_relative(path),
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha,
            }
        )

    tree = run_json(
        [f"repos/{repo}/git/trees", "--method", "POST"],
        {"base_tree": base_tree, "tree": tree_entries},
    )
    tree_sha = tree["sha"]
    if tree_sha == base_tree:
        print("No changes to commit.")
        return

    commit = run_json(
        [f"repos/{repo}/git/commits", "--method", "POST"],
        {"message": message, "tree": tree_sha, "parents": [parent_sha]},
    )
    commit_sha = commit["sha"]

    run_json(
        [f"repos/{repo}/git/refs/heads/{branch}", "--method", "PATCH"],
        {"sha": commit_sha, "force": False},
    )
    print(f"Published {commit_sha} to {repo}@{branch}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish generated site files through the GitHub API.")
    parser.add_argument("--repo", help="GitHub repository as owner/name.")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--message", required=True)
    args = parser.parse_args()
    publish(infer_repo(args.repo), args.branch, args.message)


if __name__ == "__main__":
    main()
