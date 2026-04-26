#!/usr/bin/env python3
"""
build_corpus.py — generate worker/corpus.js from markdown source files.

Sources:
  - writing/*.md              (5 essays, excludes writing/_drafts/)
  - .claude/skills/aes-*/SKILL.md   (4 skill files, skipped with warning if missing)
  - about.md

Output:
  worker/corpus.js — ES module exporting ASK_CORPUS_DOCUMENTS + ASK_CORPUS_TOKEN_ESTIMATE

Run:
  python build_corpus.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SITE = Path(__file__).resolve().parent
WORKER_DIR = SITE / "worker"

# Rough token estimate: 4 chars per token
CHARS_PER_TOKEN = 4

# Per-document character cap (~6000 tokens)
MAX_CHARS_PER_DOC = 24_000


# ---------------------------------------------------------------------------
# Markdown cleaning
# ---------------------------------------------------------------------------

def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter delimited by --- ... ---"""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:].lstrip("\n")
    return text


def strip_markdown_artifacts(text: str) -> str:
    """Remove code-fence indicators (``` lines) and compress excessive blank lines."""
    # Remove code-fence opener/closer lines (``` or ```lang) but keep the inner content
    text = re.sub(r"^```[^\n]*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*$", "", text, flags=re.MULTILINE)
    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_markdown(text: str) -> str:
    text = strip_frontmatter(text)
    text = strip_markdown_artifacts(text)
    return text


def extract_title(text: str, fallback: str) -> str:
    """Return the first # heading found, else fallback."""
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else fallback


def truncate(text: str, max_chars: int = MAX_CHARS_PER_DOC) -> str:
    if len(text) <= max_chars:
        return text
    # Truncate at a word boundary near the limit
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars - 500:
        truncated = truncated[:last_space]
    return truncated + "\n\n[truncated for context-window budget]"


# ---------------------------------------------------------------------------
# Source collection
# ---------------------------------------------------------------------------

def collect_essays() -> list[dict]:
    writing_dir = SITE / "writing"
    docs = []
    if not writing_dir.exists():
        print("  WARNING: writing/ directory not found — no essays loaded", file=sys.stderr)
        return docs
    # Exclude _drafts/
    paths = sorted(p for p in writing_dir.glob("*.md") if not p.name.startswith("_"))
    for path in paths:
        raw = path.read_text(encoding="utf-8")
        cleaned = clean_markdown(raw)
        title = extract_title(cleaned, path.stem)
        content = truncate(cleaned)
        docs.append({
            "title": title,
            "source_path": str(path.relative_to(SITE)),
            "content": content,
        })
        char_count = len(content)
        tok_est = char_count // CHARS_PER_TOKEN
        print(f"  essay   {path.name!r:45s}  {char_count:>6} chars  ~{tok_est:>5} tokens")
    return docs


def collect_skills() -> list[dict]:
    skills_dir = SITE / ".claude" / "skills"
    docs = []
    if not skills_dir.exists():
        print("  WARNING: .claude/skills/ directory not found — no skills loaded", file=sys.stderr)
        return docs
    for skill_dir in sorted(skills_dir.glob("aes-*")):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            print(f"  WARNING: {skill_file.relative_to(SITE)} not found — skipped", file=sys.stderr)
            continue
        raw = skill_file.read_text(encoding="utf-8")
        cleaned = clean_markdown(raw)
        title = extract_title(cleaned, skill_dir.name)
        # Prefix title so it's clearly a skill, not an essay
        if not title.startswith("Skill:"):
            title = f"Skill: {title}"
        content = truncate(cleaned)
        docs.append({
            "title": title,
            "source_path": str(skill_file.relative_to(SITE)),
            "content": content,
        })
        char_count = len(content)
        tok_est = char_count // CHARS_PER_TOKEN
        print(f"  skill   {skill_file.parent.name!r:45s}  {char_count:>6} chars  ~{tok_est:>5} tokens")
    return docs


def collect_about() -> list[dict]:
    about_path = SITE / "about.md"
    docs = []
    if not about_path.exists():
        print("  WARNING: about.md not found — skipped", file=sys.stderr)
        return docs
    raw = about_path.read_text(encoding="utf-8")
    cleaned = clean_markdown(raw)
    title = extract_title(cleaned, "About AES Research")
    content = truncate(cleaned)
    docs.append({
        "title": title,
        "source_path": "about.md",
        "content": content,
    })
    char_count = len(content)
    tok_est = char_count // CHARS_PER_TOKEN
    print(f"  about   {'about.md'!r:45s}  {char_count:>6} chars  ~{tok_est:>5} tokens")
    return docs


# ---------------------------------------------------------------------------
# Render corpus.js
# ---------------------------------------------------------------------------

def build_corpus_js(documents: list[dict], timestamp: str) -> str:
    """
    Serialize documents to a valid ES module.

    Each document in the Citations API shape:
      { type, source: { type, media_type, data }, title, citations }

    We use json.dumps() for the data strings so all escaping is handled
    correctly (double quotes, backslashes, control characters, etc.).
    The resulting Python string is a valid JS string literal when placed
    inside a JSON-encoded object.
    """
    total_chars = sum(len(d["content"]) for d in documents)
    total_tokens_est = total_chars // CHARS_PER_TOKEN

    # Build the JS array entries using json.dumps for safe string encoding
    entries = []
    for d in documents:
        # json.dumps produces a JSON string with correct escaping for embedding
        # in JS (JSON is valid JS for string literals, numbers, arrays, objects).
        title_js = json.dumps(d["title"])
        data_js = json.dumps(d["content"])
        entry = (
            "  {\n"
            "    type: 'document',\n"
            f"    source: {{ type: 'text', media_type: 'text/plain', data: {data_js} }},\n"
            f"    title: {title_js},\n"
            "    citations: { enabled: true },\n"
            "  }"
        )
        entries.append(entry)

    array_body = ",\n".join(entries)

    lines = [
        "// AUTO-GENERATED by build_corpus.py — do not edit manually",
        "// Run: python build_corpus.py",
        f"// Last generated: {timestamp}",
        f"// Sources: {len(documents)} documents  |  ~{total_chars:,} chars  |  ~{total_tokens_est:,} tokens",
        "",
        "export const ASK_CORPUS_DOCUMENTS = [",
        array_body,
        "];",
        "",
        f"export const ASK_CORPUS_TOKEN_ESTIMATE = {total_tokens_est};  // approximate sum (chars / 4)",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("build_corpus:")

    # Collect all sources
    essays = collect_essays()
    skills = collect_skills()
    about = collect_about()
    documents = essays + skills + about

    if not documents:
        print("  ERROR: no documents found — corpus.js not written", file=sys.stderr)
        sys.exit(1)

    total_chars = sum(len(d["content"]) for d in documents)
    total_tokens = total_chars // CHARS_PER_TOKEN

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    corpus_js = build_corpus_js(documents, timestamp)

    out_path = WORKER_DIR / "corpus.js"
    WORKER_DIR.mkdir(exist_ok=True)
    out_path.write_text(corpus_js, encoding="utf-8")

    lines = corpus_js.count("\n")
    print(f"  wrote   worker/corpus.js  ({lines} lines)")
    print(f"  total   {len(documents)} documents  |  {total_chars:,} chars  |  ~{total_tokens:,} tokens estimated")
    print("  done.")


if __name__ == "__main__":
    main()
