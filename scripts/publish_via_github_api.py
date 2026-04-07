from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PUBLISH_PATHS = [
    ".gitattributes",
    ".gitignore",
    "README.md",
    "content",
    "docs",
    "prompts",
    "scripts",
    "site",
]

TEXT_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".txt",
}
TEXT_FILENAMES = {".gitattributes", ".gitignore", ".nojekyll"}
PROXY_ENV_VARS = (
    "ALL_PROXY",
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "all_proxy",
    "https_proxy",
    "http_proxy",
)
RETRYABLE_ERRORS = (
    "eof",
    "unexpected eof",
    "connection reset",
    "connection refused",
    "forcibly closed",
    "wsarecv",
    "i/o timeout",
    "context deadline exceeded",
    "tls handshake timeout",
    "timeout",
    "temporary failure",
    "temporarily unavailable",
    "502",
    "503",
    "504",
)


def clean_network_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in PROXY_ENV_VARS:
        env.pop(key, None)
    return env


def run_json(args: list[str], payload: dict | None = None) -> dict:
    cmd = ["gh", "api", *args]
    kwargs = {
        "cwd": ROOT,
        "text": True,
        "capture_output": True,
        "check": False,
        "env": clean_network_env(),
        "timeout": 60,
    }
    if payload is not None:
        cmd.extend(["--input", "-"])
        kwargs["input"] = json.dumps(payload)

    last_error = ""
    for attempt in range(1, 6):
        try:
            result = subprocess.run(cmd, **kwargs)
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout or "{}")
                except json.JSONDecodeError as exc:
                    last_error = f"Could not parse GitHub API response: {exc}"
            else:
                last_error = result.stderr.strip() or result.stdout.strip()
        except subprocess.TimeoutExpired as exc:
            last_error = f"GitHub API request timed out after {exc.timeout} seconds."

        retryable = any(marker in last_error.lower() for marker in RETRYABLE_ERRORS)
        if not retryable or attempt == 5:
            raise SystemExit(last_error)

        delay = min(2 ** attempt, 20)
        print(f"GitHub API call failed transiently on attempt {attempt}; retrying in {delay}s: {last_error}")
        time.sleep(delay)

    raise SystemExit(last_error)


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


def is_publish_path(path: str) -> bool:
    return any(path == root or path.startswith(f"{root}/") for root in PUBLISH_PATHS)


def git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def read_blob_bytes(path: Path) -> bytes:
    if path.name in TEXT_FILENAMES or path.suffix.lower() in TEXT_EXTENSIONS:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        return text.encode("utf-8")
    return path.read_bytes()


def create_blob(repo: str, path: Path) -> str:
    content = base64.b64encode(read_blob_bytes(path)).decode("ascii")
    blob = run_json(
        [f"repos/{repo}/git/blobs", "--method", "POST"],
        {"content": content, "encoding": "base64"},
    )
    return blob["sha"]


def fetch_tree_files(repo: str, tree_sha: str) -> dict[str, str]:
    tree = run_json([f"repos/{repo}/git/trees/{tree_sha}?recursive=1"])
    if tree.get("truncated"):
        raise SystemExit("GitHub returned a truncated tree; refusing to publish an incomplete comparison.")
    return {
        item["path"]: item["sha"]
        for item in tree.get("tree", [])
        if item.get("type") == "blob"
    }


def publish(repo: str, branch: str, message: str) -> None:
    ref = run_json([f"repos/{repo}/git/ref/heads/{branch}"])
    parent_sha = ref["object"]["sha"]
    parent_commit = run_json([f"repos/{repo}/git/commits/{parent_sha}"])
    base_tree = parent_commit["tree"]["sha"]
    remote_files = fetch_tree_files(repo, base_tree)

    tree_entries = []
    local_files = {}
    for path in iter_publish_files():
        relative_path = posix_relative(path)
        content = read_blob_bytes(path)
        local_files[relative_path] = content
        if remote_files.get(relative_path) == git_blob_sha(content):
            continue
        blob_sha = create_blob(repo, path)
        tree_entries.append(
            {
                "path": relative_path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha,
            }
        )

    for remote_path in sorted(remote_files):
        if is_publish_path(remote_path) and remote_path not in local_files:
            tree_entries.append({"path": remote_path, "sha": None})

    if not tree_entries:
        print("No changes to commit.")
        return

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
