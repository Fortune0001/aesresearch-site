#!/usr/bin/env python3
"""
aes_publish — static site generator + GitHub Pages deployer for aesresearch.ai

Usage:
  python build.py              # build HTML from markdown sources
  python build.py --deploy     # build + git add + commit + push
  python build.py --all        # build + deploy + enable Pages + configure custom domain

Environment:
  GITHUB_TOKEN_FG_Admin must be set (or available in ~/.keys.env)
  REPO_SLUG env var or REPO default below identifies the target GitHub repo

Zero external dependencies beyond `markdown` (pip install markdown).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import markdown

# ---------- config ----------
REPO = os.environ.get("REPO_SLUG", "Fortune0001/aesresearch-site")
DOMAIN = os.environ.get("CUSTOM_DOMAIN", "aesresearch.ai")
SITE = Path(__file__).resolve().parent
LAYOUT = (SITE / "layouts" / "default.html").read_text(encoding="utf-8")
TOKEN_VAR = "GITHUB_TOKEN_FG_Admin"


# ---------- token loading ----------
def load_token() -> str:
    token = os.environ.get(TOKEN_VAR)
    if token:
        return token
    keys = Path.home() / ".keys.env"
    if keys.exists():
        for raw in keys.read_bytes().splitlines():
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if line.startswith(f"{TOKEN_VAR}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(f"{TOKEN_VAR} not found in env or ~/.keys.env")


def api(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict | str]:
    url = f"https://api.github.com{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
            try:
                return r.status, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else ""
        try:
            return e.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return e.code, raw


# ---------- build ----------
TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
DESC_RE = re.compile(r"^\*(.+)\*$", re.MULTILINE)


def extract_title_and_description(md: str) -> tuple[str, str]:
    title_match = TITLE_RE.search(md)
    title = title_match.group(1).strip() if title_match else "AES Research"
    # description: first italicized line after the title, if any
    desc = ""
    if title_match:
        after_title = md[title_match.end():]
        desc_match = DESC_RE.search(after_title)
        if desc_match:
            desc = desc_match.group(1).strip()
    return title, desc


def make_nav(is_article: bool) -> str:
    if is_article:
        return '<div class="nav"><a href="../index.html">&larr; AES Research</a></div>\n'
    return ""


def render_md(src: Path, dst: Path, css_rel: str, is_article: bool) -> None:
    md_text = src.read_text(encoding="utf-8")
    title, desc = extract_title_and_description(md_text)
    body_html = markdown.markdown(
        md_text,
        extensions=["fenced_code", "tables", "smarty"],
        output_format="html5",
    )
    html = LAYOUT.format(
        title=title,
        description=desc,
        css_path=css_rel,
        nav=make_nav(is_article),
        body=body_html,
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(html, encoding="utf-8")
    print(f"  built {dst.relative_to(SITE)}")


def build() -> None:
    print("build:")
    # Landing page
    render_md(SITE / "index.md", SITE / "index.html", "style.css", is_article=False)
    # Writing
    writing = SITE / "writing"
    if writing.exists():
        for md_path in sorted(writing.glob("*.md")):
            html_path = md_path.with_suffix(".html")
            render_md(md_path, html_path, "../style.css", is_article=True)
    # Ensure .nojekyll and CNAME
    (SITE / ".nojekyll").touch()
    (SITE / "CNAME").write_text(DOMAIN + "\n", encoding="utf-8")
    print("  .nojekyll + CNAME written")


# ---------- deploy ----------
def run(*args: str, check: bool = True, cwd: Path = SITE) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=check, capture_output=True, text=True)


def deploy() -> None:
    print("deploy:")
    if not (SITE / ".git").exists():
        run("git", "init", "-b", "main")
        print("  git init")
    token = load_token()
    remote_url = f"https://x-access-token:{token}@github.com/{REPO}.git"
    # Configure / re-configure origin
    existing = run("git", "remote", check=False).stdout.split()
    if "origin" in existing:
        run("git", "remote", "set-url", "origin", remote_url)
    else:
        run("git", "remote", "add", "origin", remote_url)
    # Ensure user identity for commit (repo-scoped)
    run("git", "config", "user.email", "daniel@aesresearch.ai")
    run("git", "config", "user.name", "Daniel Higuera")
    # Stage + commit
    run("git", "add", "-A")
    diff = run("git", "diff", "--staged", "--quiet", check=False)
    if diff.returncode == 0:
        print("  no changes to commit")
    else:
        run("git", "commit", "-m", "build: regenerate site")
        print("  committed")
    # Push
    push = run("git", "push", "-u", "origin", "main", check=False)
    if push.returncode != 0:
        # Try force-with-lease fallback on initial-push conflict with auto-init README
        pull = run("git", "pull", "--rebase", "origin", "main", check=False)
        run("git", "push", "-u", "origin", "main")
    print("  pushed")


# ---------- pages ----------
def enable_pages() -> None:
    print("pages:")
    token = load_token()
    # Check current state
    status, data = api("GET", f"/repos/{REPO}/pages", token=token)
    if status == 200:
        print(f"  pages already enabled: {data.get('html_url')}")
    else:
        status, data = api(
            "POST",
            f"/repos/{REPO}/pages",
            body={"source": {"branch": "main", "path": "/"}},
            token=token,
        )
        if status in (201, 202):
            print(f"  pages enabled: {data.get('html_url')}")
        else:
            print(f"  pages enable failed: HTTP {status} {data}")
            return
    # Custom domain
    status, data = api(
        "PUT",
        f"/repos/{REPO}/pages",
        body={"cname": DOMAIN, "https_enforced": True},
        token=token,
    )
    if status in (200, 204):
        print(f"  custom domain set: {DOMAIN}")
    else:
        print(f"  custom domain set failed: HTTP {status} {data}")


# ---------- main ----------
def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--deploy", action="store_true", help="git add + commit + push after build")
    p.add_argument("--pages", action="store_true", help="enable GitHub Pages + set custom domain")
    p.add_argument("--all", action="store_true", help="build + deploy + pages")
    args = p.parse_args()
    if args.all:
        args.deploy = True
        args.pages = True
    build()
    if args.deploy:
        deploy()
    if args.pages:
        enable_pages()


if __name__ == "__main__":
    main()
