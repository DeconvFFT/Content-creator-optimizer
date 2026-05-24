#!/usr/bin/env python3
"""Create Obsidian chapter-note scaffolds from lawful local PDFs.

This tool does not write raw extracted book text into tracked notes. It creates
metadata, chapter headings, and note scaffolds so a reading/summarization pass
can add compact notes without copying the source.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


FLAGGED_ORIGIN_MARKERS = (
    "anna",
    "z-library",
    "zlibrary",
    "libgen",
    "ebooksworld",
    "ebooksworld",
)


@dataclass(frozen=True)
class ChapterStub:
    number: str
    title: str
    start_line: int
    end_line: int


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "untitled"


def flagged_origin(path: Path) -> list[str]:
    lower_name = path.name.lower()
    return [marker for marker in FLAGGED_ORIGIN_MARKERS if marker in lower_name]


def extract_text(pdf_path: Path, source_text: Path | None = None) -> tuple[str, str]:
    if source_text:
        return source_text.read_text(encoding="utf-8", errors="replace"), "source_text"

    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        completed = subprocess.run(
            [pdftotext, "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return completed.stdout, "pdftotext"

    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "No PDF extractor available. Install poppler/pdftotext or PyMuPDF."
        ) from exc

    pages: list[str] = []
    with fitz.open(pdf_path) as document:  # type: ignore[attr-defined]
        for page in document:
            pages.append(page.get_text())
    return "\n".join(pages), "pymupdf"


def detect_chapters(text: str) -> list[ChapterStub]:
    lines = text.splitlines()
    matches: list[tuple[int, str, str]] = []
    chapter_pattern = re.compile(
        r"^\s*(?:chapter|CHAPTER)\s+([0-9]+|[IVXLC]+)\s*[:.\-]?\s*(.{0,120})$"
    )
    for index, line in enumerate(lines):
        clean = " ".join(line.split())
        if len(clean) > 160:
            continue
        match = chapter_pattern.match(clean)
        if not match:
            continue
        number = match.group(1)
        title = match.group(2).strip() or f"Chapter {number}"
        matches.append((index, number, title))

    if not matches:
        return [ChapterStub("whole-document", "Whole Document", 0, len(lines))]

    chapters: list[ChapterStub] = []
    for offset, (line_index, number, title) in enumerate(matches):
        next_index = matches[offset + 1][0] if offset + 1 < len(matches) else len(lines)
        chapters.append(ChapterStub(number, title, line_index, next_index))
    return chapters


def note_body(
    *,
    title: str,
    authors: str,
    pdf_path: Path,
    chapter: ChapterStub,
    extraction_method: str,
    rights_status: str,
) -> str:
    updated = datetime.now(timezone.utc).date().isoformat()
    chapter_slug = slugify(f"{chapter.number}-{chapter.title}")
    return f"""---
type: chapter-note
project: agent-studio-system-design
status: scaffold
source_title: {json.dumps(title)}
authors: {json.dumps(authors)}
chapter: {json.dumps(chapter.number)}
chapter_title: {json.dumps(chapter.title)}
source_path: {json.dumps(str(pdf_path))}
rights_status: {rights_status}
extraction_method: {extraction_method}
line_span: [{chapter.start_line}, {chapter.end_line}]
updated: {updated}
---

# {chapter.number} - {chapter.title}

## Source Metadata

- Title: {title}
- Authors: {authors or "Unknown"}
- Local source: `{pdf_path}`
- Rights status: `{rights_status}`
- Extraction method: `{extraction_method}`
- Chapter slug: `{chapter_slug}`

## Detailed Notes

Add compact notes here from a lawful reading pass. Do not paste raw source text.

## Design Patterns

## Failure Modes

## Agent Studio Implications

## Follow-Up Questions
"""


def write_notes(args: argparse.Namespace) -> dict[str, object]:
    pdf_path = Path(args.pdf).expanduser().resolve()
    vault_root = Path(args.vault_root).expanduser().resolve()
    source_text = Path(args.source_text).expanduser().resolve() if args.source_text else None

    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    markers = flagged_origin(pdf_path)
    if markers and not args.allow_flagged_origin:
        raise SystemExit(
            "Refusing to ingest likely unauthorized source marker(s) "
            f"{markers} in filename: {pdf_path.name}"
        )

    if args.rights_status not in {
        "official_open",
        "user_confirmed_lawful",
        "user_provided_local",
    }:
        raise SystemExit(
            "Refusing to write chapter notes without rights confirmation. "
            "Use --rights-status official_open, user_confirmed_lawful, "
            "or user_provided_local."
        )

    text, extraction_method = extract_text(pdf_path, source_text)
    chapters = detect_chapters(text)

    book_dir = vault_root / "02-books" / args.book_slug / "chapters"
    manifest = {
        "title": args.title,
        "authors": args.authors,
        "source_path": str(pdf_path),
        "rights_status": args.rights_status,
        "extraction_method": extraction_method,
        "chapter_count": len(chapters),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "chapters": [
            {
                "number": chapter.number,
                "title": chapter.title,
                "start_line": chapter.start_line,
                "end_line": chapter.end_line,
            }
            for chapter in chapters
        ],
    }

    if args.dry_run:
        return manifest

    book_dir.mkdir(parents=True, exist_ok=True)
    for chapter in chapters:
        note_path = book_dir / f"{slugify(f'{chapter.number}-{chapter.title}')}.md"
        note_path.write_text(
            note_body(
                title=args.title,
                authors=args.authors,
                pdf_path=pdf_path,
                chapter=chapter,
                extraction_method=extraction_method,
                rights_status=args.rights_status,
            ),
            encoding="utf-8",
        )
    manifest_path = vault_root / "05-ingestion-runs" / f"{args.book_slug}-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--book-slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--authors", default="")
    parser.add_argument(
        "--rights-status",
        choices=[
            "official_open",
            "user_confirmed_lawful",
            "user_provided_local",
            "needs_confirmation",
        ],
        default="needs_confirmation",
    )
    parser.add_argument("--source-text")
    parser.add_argument(
        "--vault-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    parser.add_argument("--allow-flagged-origin", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest = write_notes(args)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
