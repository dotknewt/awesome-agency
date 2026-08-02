#!/usr/bin/env python3
"""Check that every prose paragraph in a markdown file stays under a character limit.

Self-contained, standard-library only (no third-party dependencies).

Usage:
  validate_paragraphs.py [OPTIONS] FILE

Parses FILE as markdown, groups lines into blocks separated by blank lines,
classifies each block (heading, fenced code, blockquote, list item, or
paragraph), and checks the length of each block's joined text against
--limit (default 240) characters.

By default, only plain prose paragraphs are checked. Headings and fenced
code blocks are always skipped (they are not prose). Blockquotes and list
items are skipped by default too, since quoted or itemized material often
can't be shortened without changing its meaning -- pass --check-blockquotes
or --check-list-items to include them.

Output:
  A single JSON object is written to stdout describing the run, including
  a "violations" array for any block that exceeded the limit. All
  progress/diagnostic messages go to stderr, so stdout stays valid,
  parseable JSON.

Examples:
  validate_paragraphs.py article.md
  validate_paragraphs.py --limit 200 article.md
  validate_paragraphs.py --check-blockquotes --check-list-items article.md
  validate_paragraphs.py --limit 240 - < article.md

Exit codes:
  0  success, no paragraphs exceeded the limit
  1  success, but one or more paragraphs exceeded the limit
  2  usage error (bad arguments)
  3  input error (file not found / not readable / not decodable as UTF-8)
"""

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_LIMIT = 240

FENCE_RE = re.compile(r"^(```|~~~)")
HEADING_RE = re.compile(r"^#{1,6}\s")
BLOCKQUOTE_RE = re.compile(r"^\s{0,3}>")
LIST_ITEM_RE = re.compile(r"^\s{0,3}([-*+]|\d+[.)])\s")


def classify_block(lines):
    """Classify a block of non-blank lines as one markdown block type."""
    first = lines[0]
    if HEADING_RE.match(first):
        return "heading"
    if BLOCKQUOTE_RE.match(first):
        return "blockquote"
    if LIST_ITEM_RE.match(first):
        return "list_item"
    return "paragraph"


def strip_prefix(block_type, line):
    """Strip markdown-structural prefixes so length checks reflect prose content."""
    if block_type == "blockquote":
        return BLOCKQUOTE_RE.sub("", line, count=1).strip()
    if block_type == "list_item":
        return LIST_ITEM_RE.sub("", line, count=1).strip()
    if block_type == "heading":
        return HEADING_RE.sub("", line, count=1).strip()
    return line.strip()


def extract_blocks(text):
    """Split markdown text into blocks, tracking fenced code regions and line numbers.

    Returns a list of dicts: {type, start_line, end_line, text}.
    Blocks inside fenced code regions are reported with type "code_block" and
    are never split further (the whole fence is one block).
    """
    blocks = []
    lines = text.splitlines()

    in_fence = False
    fence_marker = None
    current_lines = []
    current_start = None

    def flush():
        nonlocal current_lines, current_start
        if not current_lines:
            return
        block_type = classify_block(current_lines)
        joined = " ".join(
            strip_prefix(block_type, line) for line in current_lines if line.strip()
        )
        joined = re.sub(r"\s+", " ", joined).strip()
        blocks.append(
            {
                "type": block_type,
                "start_line": current_start,
                "end_line": current_start + len(current_lines) - 1,
                "text": joined,
            }
        )
        current_lines = []
        current_start = None

    code_start = None
    code_lines = []
    for i, raw_line in enumerate(lines, start=1):
        fence_match = FENCE_RE.match(raw_line.strip())
        if fence_match:
            if not in_fence:
                flush()
                in_fence = True
                fence_marker = fence_match.group(1)
                code_start = i
                code_lines = [raw_line]
            else:
                code_lines.append(raw_line)
                if raw_line.strip().startswith(fence_marker):
                    blocks.append(
                        {
                            "type": "code_block",
                            "start_line": code_start,
                            "end_line": i,
                            "text": "\n".join(code_lines),
                        }
                    )
                    in_fence = False
                    fence_marker = None
                    code_lines = []
                    code_start = None
            continue

        if in_fence:
            code_lines.append(raw_line)
            continue

        if raw_line.strip() == "":
            flush()
            continue

        if current_start is None:
            current_start = i
        current_lines.append(raw_line)

    if in_fence:
        # Unterminated fence: treat whatever we collected as a trailing code block
        # rather than silently discarding it or crashing.
        blocks.append(
            {
                "type": "code_block",
                "start_line": code_start,
                "end_line": lines and len(lines) or code_start,
                "text": "\n".join(code_lines),
            }
        )
    else:
        flush()

    return blocks


def excerpt(text, max_len=80):
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="validate_paragraphs.py",
        description=(
            "Check that every prose paragraph in a markdown file stays under a "
            "character limit (default 240). Reports offending paragraphs, with "
            "their line location, as JSON on stdout."
        ),
        epilog=(
            "Examples:\n"
            "  validate_paragraphs.py article.md\n"
            "  validate_paragraphs.py --limit 200 article.md\n"
            "  validate_paragraphs.py --check-blockquotes --check-list-items article.md\n"
            "  validate_paragraphs.py - < article.md\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file",
        help="Path to the markdown file to check. Use '-' to read from stdin.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum characters allowed per paragraph (default: {DEFAULT_LIMIT}).",
    )
    parser.add_argument(
        "--check-blockquotes",
        action="store_true",
        help="Also check blockquote (> ...) blocks against the limit. Off by default, "
        "since quoted material often can't be shortened without changing its meaning.",
    )
    parser.add_argument(
        "--check-list-items",
        action="store_true",
        help="Also check individual list items against the limit. Off by default.",
    )

    args = parser.parse_args(argv)

    if args.limit <= 0:
        parser.error("--limit must be a positive integer")

    if args.file == "-":
        try:
            text = sys.stdin.read()
        except Exception as exc:  # pragma: no cover - defensive
            print(f"Error: failed to read from stdin: {exc}", file=sys.stderr)
            return 3
        source_name = "<stdin>"
    else:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            return 3
        if not path.is_file():
            print(f"Error: not a regular file: {args.file}", file=sys.stderr)
            return 3
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            print(f"Error: {args.file} is not valid UTF-8: {exc}", file=sys.stderr)
            return 3
        except OSError as exc:
            print(f"Error: could not read {args.file}: {exc}", file=sys.stderr)
            return 3
        source_name = str(args.file)

    print(f"Checking {source_name} against a {args.limit}-character paragraph limit...", file=sys.stderr)

    blocks = extract_blocks(text)

    checked_types = {"paragraph"}
    if args.check_blockquotes:
        checked_types.add("blockquote")
    if args.check_list_items:
        checked_types.add("list_item")

    skipped_counts = {"code_block": 0, "heading": 0, "blockquote": 0, "list_item": 0}
    violations = []
    checked_count = 0

    for block in blocks:
        block_type = block["type"]
        if block_type not in checked_types:
            if block_type in skipped_counts:
                skipped_counts[block_type] += 1
            continue
        if not block["text"]:
            continue
        checked_count += 1
        length = len(block["text"])
        if length > args.limit:
            violations.append(
                {
                    "line": block["start_line"],
                    "end_line": block["end_line"],
                    "type": block_type,
                    "length": length,
                    "excerpt": excerpt(block["text"]),
                }
            )

    result = {
        "file": source_name,
        "limit": args.limit,
        "checked_paragraphs": checked_count,
        "violations": violations,
        "skipped": skipped_counts,
        "ok": len(violations) == 0,
    }

    print(json.dumps(result, indent=2))

    if violations:
        print(
            f"Found {len(violations)} paragraph(s) exceeding {args.limit} characters.",
            file=sys.stderr,
        )
        return 1

    print(f"All {checked_count} checked paragraph(s) are within the limit.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - defensive catch-all
        print(f"Error: unexpected failure: {exc}", file=sys.stderr)
        sys.exit(2)
