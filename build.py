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
import html
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
TOKEN_VARS = ("GITHUB_TOKEN_CLASSIC", "GITHUB_TOKEN_FG_Admin")  # prefer classic; fall back to fine-grained

# ---------- licensing / citation metadata ----------
SITE_URL = "https://aesresearch.ai"
CITATION_META_PATH = SITE / "citation_meta.json"
if CITATION_META_PATH.exists():
    CITATION_META: dict = json.loads(CITATION_META_PATH.read_text(encoding="utf-8"))
else:
    CITATION_META = {}


def canonical_url_for(dst: Path) -> str:
    """Absolute canonical URL for a rendered page. Root index.html -> bare domain root."""
    if dst == SITE / "index.html":
        return f"{SITE_URL}/"
    return f"{SITE_URL}/{dst.relative_to(SITE).as_posix()}"


def license_href_for(css_rel: str) -> str:
    """Mirror css_path's relative-depth convention for the footer license link."""
    return css_rel.replace("style.css", "license.html")


def build_article_head_extra(slug: str, title: str, canonical: str) -> str:
    """Highwire citation meta + ScholarlyArticle JSON-LD for an essay with a
    citation_meta.json entry. Missing entries degrade to '' with a warning
    (do not fail the build)."""
    meta = CITATION_META.get(slug)
    if not meta:
        print(f"  WARNING: no citation_meta.json entry for essay '{slug}' — head_extra left empty")
        return ""
    date = meta["date"]  # YYYY-MM-DD
    y, m, d = date.split("-")
    title_attr = html.escape(title, quote=True)
    highwire = (
        f'  <meta name="citation_title" content="{title_attr}">\n'
        f'  <meta name="citation_author" content="Daniel Higuera">\n'
        f'  <meta name="citation_publication_date" content="{y}/{m}/{d}">\n'
        f'  <meta name="citation_fulltext_html_url" content="{canonical}">\n'
        f'  <meta name="citation_language" content="en">\n'
        f'  <meta name="citation_publisher" content="AES Research">\n'
    )
    ld = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": title,
        "author": {"@type": "Person", "name": "Daniel Higuera"},
        "publisher": {"@type": "Organization", "name": "AES Research", "url": f"{SITE_URL}/"},
        "datePublished": date,
        "license": "https://creativecommons.org/licenses/by-sa/4.0/",
        "url": canonical,
        "inLanguage": "en",
    }
    script = f'  <script type="application/ld+json">\n{json.dumps(ld, indent=2)}\n  </script>\n'
    return highwire + script


def build_home_head_extra(canonical: str) -> str:
    """WebSite JSON-LD for the homepage."""
    ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "AES Research",
        "url": canonical,
    }
    return f'  <script type="application/ld+json">\n{json.dumps(ld, indent=2)}\n  </script>\n'


# ---------- token loading ----------
def load_token() -> str:
    for var in TOKEN_VARS:
        t = os.environ.get(var)
        if t:
            return t
    keys = Path.home() / ".keys.env"
    if keys.exists():
        for raw in keys.read_bytes().splitlines():
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            for var in TOKEN_VARS:
                if line.startswith(f"{var}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(f"No token found. Set one of {TOKEN_VARS} in env or ~/.keys.env")


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
    # description: first italicized OR bold line after the title.
    # DESC_RE matches both `*X*` and `**X**` (it captures the inner content). For
    # bold input, the captured group is `*X*` — strip leading/trailing asterisks
    # so the meta description doesn't render literal stars.
    desc = ""
    if title_match:
        after_title = md[title_match.end():]
        desc_match = DESC_RE.search(after_title)
        if desc_match:
            desc = desc_match.group(1).strip().strip("*").strip()
            desc = strip_inline_markdown(desc)
    # Fallback for pages whose lead is raw HTML (e.g. the homepage's
    # <p class="lede">/<p class="subtitle">) rather than a markdown *italic* line,
    # so the meta/OG description isn't empty.
    if not desc:
        hm = re.search(r'<p class="lede">(.+?)</p>', md, re.DOTALL) \
            or re.search(r'<p class="subtitle">(.+?)</p>', md, re.DOTALL)
        if hm:
            desc = html.unescape(re.sub(r'<[^>]+>', '', hm.group(1)))
            desc = re.sub(r'\s+', ' ', desc).strip()
    return title, desc


def strip_inline_markdown(text: str) -> str:
    """Reduce inline markdown to plain text for use in a meta description.

    Meta descriptions are plain-text attributes; leaving `[label](url)` or `**x**`
    in them renders literal markdown in search results, social cards, and tab
    previews. Collapse links to their label and drop emphasis/code markers.
    """
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # [label](url) -> label
    text = re.sub(r"`([^`]+)`", r"\1", text)               # `code` -> code
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)          # **bold** -> bold
    text = re.sub(r"\*([^*]+)\*", r"\1", text)              # *italic* -> italic
    return re.sub(r"\s+", " ", text).strip()


def word_count(md_text: str) -> int:
    text = re.sub(r"```.*?```", "", md_text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", "", text)
    text = re.sub(r"[#*_>\-\[\]\(\)!]", " ", text)
    return len([w for w in text.split() if w])


def reading_time_min(md_text: str) -> int:
    return max(1, round(word_count(md_text) / 220))


def file_dates(path: Path) -> tuple[str, str]:
    """Return (published_iso, updated_iso) as YYYY-MM-DD; git log first/last commit, mtime fallback."""
    first, last = "", ""
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--follow", "--format=%aI", "--", str(path.name)],
            cwd=path.parent, capture_output=True, text=True, check=False
        )
        if out.returncode == 0 and out.stdout.strip():
            first = out.stdout.strip().splitlines()[-1]
        out2 = subprocess.run(
            ["git", "log", "-1", "--format=%aI", "--", str(path.name)],
            cwd=path.parent, capture_output=True, text=True, check=False
        )
        if out2.returncode == 0 and out2.stdout.strip():
            last = out2.stdout.strip()
    except Exception:
        pass
    if not first or not last:
        from datetime import datetime, timezone
        ts = path.stat().st_mtime
        iso = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        first = first or iso
        last = last or iso
    return first[:10], last[:10]


def make_nav(kind: str, root_path: str = "index.html") -> str:
    """Render the top-of-page nav as a real <nav> landmark.
    kind: 'home' (no nav) | 'subpage' (back-link only) | 'essay' (back + breadcrumb)
    root_path: path to root index.html, relative to the rendered page.
    """
    if kind == "essay":
        return ('<nav class="nav" aria-label="Breadcrumb"><a href="../index.html">&larr; AES Research</a>'
                ' <span class="sep">/</span> <a href="index.html">Writing</a></nav>\n')
    if kind == "subpage":
        return f'<nav class="nav" aria-label="Breadcrumb"><a href="{root_path}">&larr; AES Research</a></nav>\n'
    return ""


def render_md(src: Path, dst: Path, css_rel: str, is_article: bool,
              prev_slug: str | None = None, next_slug: str | None = None,
              nav_kind: str | None = None, nav_root: str = "index.html",
              head_extra: str = "") -> None:
    md_text = src.read_text(encoding="utf-8")
    title, desc = extract_title_and_description(md_text)
    body_html = markdown.markdown(
        md_text,
        extensions=["fenced_code", "tables", "smarty", "toc"],
        output_format="html5",
    )

    if is_article:
        published, updated = file_dates(src)
        rt = reading_time_min(md_text)
        meta = f'<p class="article-meta">Published {published}'
        if updated and updated != published:
            meta += f' · Updated {updated}'
        meta += f' · {rt} min read</p>'
        body_html = re.sub(r"(</h1>)", r"\1\n" + meta, body_html, count=1)

        nav_links = []
        if prev_slug:
            nav_links.append(f'<a href="{prev_slug}.html">&larr; Previous</a>')
        if next_slug:
            nav_links.append(f'<a href="{next_slug}.html">Next &rarr;</a>')
        prev_next = (f'<p class="prev-next">{" · ".join(nav_links)}</p>'
                     if nav_links else "")
        wayfinding = ('<p class="wayfinding">AES Research is a public lab for '
                      'agent-system patterns from production. '
                      '<a href="index.html">More writing &rarr;</a></p>')
        body_html += f'\n<div class="post-footer">{prev_next}{wayfinding}</div>'

    # Default nav resolution: essay → essay breadcrumb; non-essay subpages get a
    # plain back-link unless caller overrides; root index gets nothing.
    if nav_kind is None:
        if is_article:
            nav_kind = "essay"
        elif dst.name == "index.html" and dst.parent == SITE:
            nav_kind = "home"
        else:
            nav_kind = "subpage"
    # Page title pattern: "Page Title — AES Research" (except for the home index,
    # which is just "AES Research"). Improves WCAG 2.4.2 distinctness across pages
    # and makes browser tabs / OG embeds readable.
    is_home = (dst.name == "index.html" and dst.parent == SITE)
    title_full = title if (is_home or title == "AES Research") else f"{title} — AES Research"
    page_html = LAYOUT.format(
        title=title,
        title_full=title_full,
        description=desc,
        css_path=css_rel,
        canonical_url=canonical_url_for(dst),
        head_extra=head_extra,
        license_href=license_href_for(css_rel),
        nav=make_nav(nav_kind, root_path=nav_root),
        body=body_html,
        footer_tagline="",
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(page_html, encoding="utf-8")
    print(f"  built {dst.relative_to(SITE)}")


def build() -> None:
    print("build:")
    # Regenerate worker corpus from markdown sources before rendering HTML
    result = subprocess.run(
        [sys.executable, str(SITE / "build_corpus.py")],
        cwd=SITE, capture_output=False, text=True, check=False,
    )
    if result.returncode != 0:
        print(f"  WARNING: build_corpus.py exited {result.returncode} — continuing build")
    # Landing page
    render_md(SITE / "index.md", SITE / "index.html", "style.css", is_article=False,
              head_extra=build_home_head_extra(canonical_url_for(SITE / "index.html")))
    # Contact page (if present)
    if (SITE / "contact.md").exists():
        render_md(SITE / "contact.md", SITE / "contact.html", "style.css", is_article=False)
    # Ask / Q&A page (if present)
    if (SITE / "ask.md").exists():
        render_md(SITE / "ask.md", SITE / "ask.html", "style.css", is_article=False)
    # Pillar pages
    if (SITE / "skills.md").exists():
        render_md(SITE / "skills.md", SITE / "skills.html", "style.css", is_article=False)
    if (SITE / "about.md").exists():
        render_md(SITE / "about.md", SITE / "about.html", "style.css", is_article=False)
    # Licensing & citation page
    if (SITE / "license.md").exists():
        render_md(SITE / "license.md", SITE / "license.html", "style.css", is_article=False)
    # Writing index lives in writing/ subdirectory so it shares URL space with the essays
    if (SITE / "writing-index.md").exists():
        (SITE / "writing").mkdir(exist_ok=True)
        render_md(SITE / "writing-index.md", SITE / "writing" / "index.html", "../style.css",
                  is_article=False, nav_kind="subpage", nav_root="../index.html")
    # Writing
    writing = SITE / "writing"
    if writing.exists():
        essays = sorted(writing.glob("*.md"))
        # Stub guard: essay sources whose canonical content moved to the warehouse are
        # 6-line "MOVED" stubs. Rendering one would overwrite (and on deploy, destroy)
        # the live essay HTML. Fail closed: refuse to build until the source is restored.
        stubbed = [p.name for p in essays
                   if "# MOVED" in p.read_text(encoding="utf-8", errors="replace")[:400]]
        if stubbed:
            raise SystemExit(
                "REFUSING TO BUILD: stub-swapped essay source(s) would clobber live HTML: "
                + ", ".join(stubbed)
                + "\nRestore full .md content (canonical copies: Research_Warehouse/articles/landing_site/) "
                  "or remove the stub files before building.")
        for i, md_path in enumerate(essays):
            html_path = md_path.with_suffix(".html")
            prev_slug = essays[i-1].stem if i > 0 else None
            next_slug = essays[i+1].stem if i < len(essays) - 1 else None
            slug = md_path.stem
            essay_title, _ = extract_title_and_description(md_path.read_text(encoding="utf-8"))
            head_extra = build_article_head_extra(slug, essay_title, canonical_url_for(html_path))
            render_md(md_path, html_path, "../style.css", is_article=True,
                      prev_slug=prev_slug, next_slug=next_slug, head_extra=head_extra)
    # Ensure .nojekyll
    (SITE / ".nojekyll").touch()
    # CNAME only when --with-cname is passed; otherwise site serves at github.io default
    cname_path = SITE / "CNAME"
    if os.environ.get("WRITE_CNAME") == "1":
        cname_path.write_text(DOMAIN + "\n", encoding="utf-8")
        print(f"  .nojekyll written; CNAME set to {DOMAIN}")
    else:
        if cname_path.exists():
            cname_path.unlink()
            print("  .nojekyll written; CNAME removed (domain not live yet)")
        else:
            print("  .nojekyll written; no CNAME (domain not live yet)")


# ---------- deploy ----------
def run(*args: str, check: bool = True, cwd: Path = SITE) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=check, capture_output=True, text=True)


def deploy() -> None:
    print("deploy:")
    if not (SITE / ".git").exists():
        run("git", "init", "-b", "main")
        print("  git init")
    token = load_token()
    # Plain remote URL — the token is passed per-invocation via an HTTP header
    # at push time and is never persisted into .git/config (Review #22 F10).
    remote_url = f"https://github.com/{REPO}.git"
    existing = run("git", "remote", check=False).stdout.split()
    if "origin" in existing:
        run("git", "remote", "set-url", "origin", remote_url)
    else:
        run("git", "remote", "add", "origin", remote_url)
    # Ensure user identity for commit (repo-scoped)
    # Use contact@aesresearch.ai for commit author — matches the address that's
    # actually routable via Cloudflare Email Routing. daniel@ has no MX route.
    run("git", "config", "user.email", "contact@aesresearch.ai")
    run("git", "config", "user.name", "Daniel Higuera")
    # Stage + commit — explicit allowlist only (Review #22 F2). `git add -A`
    # swept unrelated in-flight working-tree files into public deploys.
    allow = [
        ".gitignore", ".nojekyll", "CNAME", "404.html",
        "build.py", "build_corpus.py", "style.css", "layouts/default.html",
        "index.md", "index.html", "about.md", "about.html",
        "contact.md", "contact.html", "ask.md", "ask.html",
        "skills.md", "skills.html", "writing-index.md",
        "writing/index.html", "worker/corpus.js",
        "license.md", "license.html", "citation_meta.json",
        "robots.txt", "ai.txt", ".well-known/tdmrep.json",
    ]
    allow += [f"writing/{p.name}" for p in sorted((SITE / "writing").glob("*.md"))]
    allow += [f"writing/{p.name}" for p in sorted((SITE / "writing").glob("*.html"))]
    run("git", "add", "--", *[p for p in dict.fromkeys(allow) if (SITE / p).exists()])
    diff = run("git", "diff", "--staged", "--quiet", check=False)
    if diff.returncode == 0:
        print("  no changes to commit")
    else:
        run("git", "commit", "-m", "build: regenerate site")
        print("  committed")
    # Push — de-facto trunk is a session branch; local `main` is stale by design.
    # Pushing HEAD:main deploys the current checkout without touching local main.
    # Auth via ephemeral header; nothing token-shaped touches disk.
    import base64
    auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    run("git", "-c", f"http.https://github.com/.extraheader=AUTHORIZATION: basic {auth}",
        "push", "origin", "HEAD:main")
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
    # Custom domain (only when WRITE_CNAME=1; otherwise leave/clear to serve on github.io default)
    if os.environ.get("WRITE_CNAME") == "1":
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
    else:
        # Ensure no stale cname is stuck in Pages config
        api("PUT", f"/repos/{REPO}/pages", body={"cname": None, "https_enforced": False}, token=token)
        print(f"  custom domain cleared (serving at {data.get('html_url') if isinstance(data, dict) else 'github.io default'})")


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
