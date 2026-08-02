#!/usr/bin/env python3
"""claim_ticket.py -- Close wayfinder's tracker race windows.

wayfinder (see ../SKILL.md) expects multiple agent sessions to work the
same map concurrently ("expect other sessions to be editing the tracker
concurrently"). Two hazards fall out of that:

  1. Claiming a ticket. SKILL.md says a session must set `wayfinder:claimed`
     "first, before any work, so concurrent sessions skip it" -- but a
     plain read-labels-then-add-label sequence is NOT atomic over the
     GitHub REST API: two sessions can both read "unclaimed" before either
     one's write lands, and both start the same ticket.

  2. Wiring blocking edges. SKILL.md's "create-then-wire" two-pass flow
     draws blocking edges between ticket ids that were often created only
     moments before ("issues need ids before they can reference each
     other"). A stale or mistyped id produces a blocking edge to nothing.

This script provides one subcommand for each hazard:

  claim_ticket.py claim        Claim a ticket without losing the race.
  claim_ticket.py verify-refs  Confirm a list of issue numbers exist (and
                                are open) before you wire edges to them.

How `claim` closes the race window
-----------------------------------
The GitHub REST API has no compare-and-swap for labels. Instead, this
script uses an append-only *claim comment* as the real lock, and only
applies the `wayfinder:claimed` label after winning that lock:

  1. Post a comment containing a unique marker for this session.
  2. Re-fetch the issue's comments and find every claim-marker comment.
  3. Comment ids are assigned by GitHub in strict creation order, so the
     comment with the LOWEST id is whichever session's claim landed
     first -- even if two sessions post within the same second.
  4. If this session's comment has the lowest id, it won the race: apply
     the `wayfinder:claimed` label and exit 0.
  5. Otherwise, this session lost: do not touch the label, and exit
     EXIT_ALREADY_CLAIMED so the caller picks a different ticket.

Backends
--------
Both subcommands run against:

  * the real GitHub REST API (needs a token: --token or $GITHUB_TOKEN), or
  * a local JSON file that stands in for a repo's issues, fully offline,
    no credentials needed: --offline-store PATH (created if missing).

The offline backend implements the identical claim/verify logic, so it is
a faithful way to test this script -- including the race-losing path --
without touching the network.

Exit codes
----------
  0   success (ticket claimed, or every referenced ticket exists)
  2   usage error (bad or missing arguments)
  4   network or tracker API error
  5   the ticket named by --issue does not exist
  6   verify-refs: one or more referenced tickets are missing or not open
  10  claim: the ticket was already claimed (by this run or a concurrent
      one) -- pick a different frontier ticket

Examples
--------
  # Claim issue 482 in acme/webapp, talking to the real API:
  GITHUB_TOKEN=ghp_xxx python3 claim_ticket.py claim --repo acme/webapp --issue 482

  # Same, fully offline, for testing:
  python3 claim_ticket.py claim --repo acme/webapp --issue 482 \\
      --offline-store /tmp/fake-tracker.json --session-id session-a

  # Before wiring blocking edges, confirm 91, 92 and 93 all exist and are open:
  python3 claim_ticket.py verify-refs --repo acme/webapp --refs 91,92,93 \\
      --offline-store /tmp/fake-tracker.json
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

EXIT_OK = 0
EXIT_USAGE_ERROR = 2
EXIT_API_ERROR = 4
EXIT_NOT_FOUND = 5
EXIT_MISSING_REFS = 6
EXIT_ALREADY_CLAIMED = 10

DEFAULT_LABEL = "wayfinder:claimed"
CLAIM_MARKER_PREFIX = "<!-- wayfinder:claim"
API_ROOT = "https://api.github.com"


def emit(status, **fields):
    """Print one structured JSON object to stdout."""
    payload = {"status": status}
    payload.update(fields)
    print(json.dumps(payload, indent=2, sort_keys=True))


def diag(message):
    """Print a diagnostic/progress line to stderr."""
    print(f"claim_ticket.py: {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Backends. Both expose the same four operations so `claim()`/`verify_refs()`
# below don't need to know whether they're talking to GitHub or a local file.
# ---------------------------------------------------------------------------


class TrackerError(Exception):
    def __init__(self, message, exit_code=EXIT_API_ERROR):
        super().__init__(message)
        self.exit_code = exit_code


class GitHubBackend:
    """Talks to the real GitHub REST API over HTTPS."""

    def __init__(self, repo, token):
        if "/" not in repo:
            raise TrackerError(
                f"--repo must be OWNER/REPO, got {repo!r}", EXIT_USAGE_ERROR
            )
        self.owner, self.name = repo.split("/", 1)
        self.token = token

    def _request(self, method, path, body=None):
        url = f"{API_ROOT}/repos/{self.owner}/{self.name}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "wayfinder-claim-ticket-script")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            detail = exc.read().decode("utf-8", "replace")
            raise TrackerError(
                f"GitHub API {method} {path} failed: {exc.code} {detail}",
                EXIT_API_ERROR,
            ) from exc
        except urllib.error.URLError as exc:
            raise TrackerError(
                f"Could not reach GitHub API: {exc.reason}", EXIT_API_ERROR
            ) from exc

    def get_issue(self, number):
        issue = self._request("GET", f"/issues/{number}")
        if issue is None:
            return None
        return {
            "number": number,
            "state": issue.get("state", "open"),
            "labels": [
                lbl["name"] if isinstance(lbl, dict) else lbl
                for lbl in issue.get("labels", [])
            ],
        }

    def get_comments(self, number):
        comments = self._request("GET", f"/issues/{number}/comments") or []
        return [{"id": c["id"], "body": c.get("body", "")} for c in comments]

    def post_comment(self, number, body):
        comment = self._request(
            "POST", f"/issues/{number}/comments", {"body": body}
        )
        return {"id": comment["id"], "body": comment.get("body", "")}

    def add_label(self, number, label):
        self._request("POST", f"/issues/{number}/labels", {"labels": [label]})


class OfflineBackend:
    """Simulates a repo's issues in a local JSON file. No network calls.

    Store shape:
        {
          "issues": {
            "482": {"state": "open", "labels": [], "comments": []}
          },
          "next_comment_id": 1
        }
    """

    def __init__(self, path):
        self.path = path
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as fh:
                self.store = json.load(fh)
        else:
            self.store = {"issues": {}, "next_comment_id": 1}
            self._save()

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.store, fh, indent=2, sort_keys=True)

    def _issue(self, number, create=False):
        key = str(number)
        issues = self.store["issues"]
        if key not in issues:
            if not create:
                return None
            issues[key] = {"state": "open", "labels": [], "comments": []}
        return issues[key]

    def get_issue(self, number):
        issue = self._issue(number)
        if issue is None:
            return None
        return {
            "number": number,
            "state": issue["state"],
            "labels": list(issue["labels"]),
        }

    def get_comments(self, number):
        issue = self._issue(number)
        if issue is None:
            return []
        return [dict(c) for c in issue["comments"]]

    def post_comment(self, number, body):
        issue = self._issue(number, create=True)
        comment_id = self.store["next_comment_id"]
        self.store["next_comment_id"] += 1
        comment = {"id": comment_id, "body": body}
        issue["comments"].append(comment)
        self._save()
        return dict(comment)

    def add_label(self, number, label):
        issue = self._issue(number, create=True)
        if label not in issue["labels"]:
            issue["labels"].append(label)
        self._save()


# ---------------------------------------------------------------------------
# Core logic, backend-agnostic.
# ---------------------------------------------------------------------------


def claim(backend, issue, label, session_id, dry_run):
    issue_data = backend.get_issue(issue)
    if issue_data is None:
        emit("error", reason="not_found", issue=issue)
        return EXIT_NOT_FOUND

    if label in issue_data["labels"]:
        emit(
            "already_claimed",
            issue=issue,
            label=label,
            reason="label_already_present",
        )
        return EXIT_ALREADY_CLAIMED

    if dry_run:
        emit(
            "dry_run",
            issue=issue,
            label=label,
            session_id=session_id,
            note="no comment posted, no label applied",
        )
        return EXIT_OK

    marker = f"{CLAIM_MARKER_PREFIX} session={session_id} ts={int(time.time())} -->"
    body = f"Claiming this ticket for session `{session_id}`.\n{marker}"
    diag(f"posting claim comment for session {session_id} on issue {issue}")
    our_comment = backend.post_comment(issue, body)

    comments = backend.get_comments(issue)
    claim_comments = [c for c in comments if CLAIM_MARKER_PREFIX in c["body"]]
    if not claim_comments:
        # Should be impossible -- we just posted one -- but don't assume.
        raise TrackerError(
            "posted a claim comment but could not read it back", EXIT_API_ERROR
        )
    winner = min(claim_comments, key=lambda c: c["id"])

    if winner["id"] == our_comment["id"]:
        backend.add_label(issue, label)
        emit(
            "claimed",
            issue=issue,
            label=label,
            session_id=session_id,
            claim_comment_id=our_comment["id"],
        )
        return EXIT_OK

    emit(
        "already_claimed",
        issue=issue,
        label=label,
        reason="lost_race",
        winning_comment_id=winner["id"],
        our_comment_id=our_comment["id"],
    )
    return EXIT_ALREADY_CLAIMED


def verify_refs(backend, refs, any_state):
    checked = []
    missing = []
    not_open = []
    for number in refs:
        issue_data = backend.get_issue(number)
        checked.append(number)
        if issue_data is None:
            missing.append(number)
        elif not any_state and issue_data["state"] != "open":
            not_open.append(number)

    ok = not missing and not not_open
    emit(
        "ok" if ok else "invalid_refs",
        checked=checked,
        missing=missing,
        not_open=not_open,
    )
    return EXIT_OK if ok else EXIT_MISSING_REFS


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="claim_ticket.py",
        description=(
            "Atomically claim a wayfinder ticket, or verify that ticket "
            "references exist before wiring blocking edges between them."
        ),
        epilog=(
            "Exit codes: 0 ok, 2 usage error, 4 API error, 5 issue not "
            "found, 6 missing/not-open refs (verify-refs), 10 already "
            "claimed (claim)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--repo",
        default="offline/example",
        help="OWNER/REPO. Required for the live backend; cosmetic only "
        "for --offline-store (default: offline/example).",
    )
    common.add_argument(
        "--token",
        default=None,
        help="GitHub token. Falls back to $GITHUB_TOKEN. Ignored with "
        "--offline-store.",
    )
    common.add_argument(
        "--offline-store",
        metavar="PATH",
        default=None,
        help="Run fully offline against a local JSON file standing in "
        "for the repo's issues (created if it doesn't exist). No "
        "network calls, no credentials needed. Use this to test the "
        "script itself.",
    )

    claim_p = sub.add_parser(
        "claim",
        parents=[common],
        help="Claim a ticket, closing the race window against concurrent sessions.",
        description=(
            "Claim a ticket by posting a claim comment and only applying "
            "wayfinder:claimed if this session's comment is the first "
            "one recorded. Exits 10 (not an error) if another session "
            "already claimed it."
        ),
    )
    claim_p.add_argument(
        "--issue", type=int, required=True, help="Issue/ticket number to claim."
    )
    claim_p.add_argument(
        "--label",
        default=DEFAULT_LABEL,
        help=f"Label to apply on a successful claim (default: {DEFAULT_LABEL}).",
    )
    claim_p.add_argument(
        "--session-id",
        default=None,
        help="Identifier for this session in the claim comment. Default: "
        "a random uuid4.",
    )
    claim_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Check whether the ticket is already claimed, but don't "
        "post a comment or apply the label.",
    )

    verify_p = sub.add_parser(
        "verify-refs",
        parents=[common],
        help="Confirm referenced issue numbers exist before wiring blocking edges.",
        description=(
            "Confirm every issue number in --refs exists (and, unless "
            "--any-state is given, is open) before you wire blocking "
            "edges between them."
        ),
    )
    refs_group = verify_p.add_mutually_exclusive_group(required=True)
    refs_group.add_argument(
        "--refs",
        default=None,
        help="Comma-separated issue numbers, e.g. --refs 91,92,93.",
    )
    refs_group.add_argument(
        "--refs-file",
        default=None,
        metavar="PATH",
        help="Path to a file with one issue number per line ('-' for stdin).",
    )
    verify_p.add_argument(
        "--any-state",
        action="store_true",
        help="Accept closed issues too (default: require every ref to be open).",
    )

    return parser


def parse_refs(args):
    if args.refs is not None:
        raw_items = args.refs.split(",")
    else:
        text = (
            sys.stdin.read()
            if args.refs_file == "-"
            else open(args.refs_file, "r", encoding="utf-8").read()
        )
        raw_items = text.splitlines()

    refs = []
    for item in raw_items:
        item = item.strip()
        if not item:
            continue
        try:
            refs.append(int(item))
        except ValueError:
            raise TrackerError(
                f"not a valid issue number: {item!r}", EXIT_USAGE_ERROR
            )
    if not refs:
        raise TrackerError("no issue numbers given", EXIT_USAGE_ERROR)
    return refs


def make_backend(args):
    if args.offline_store:
        return OfflineBackend(args.offline_store)
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise TrackerError(
            "no GitHub token: pass --token, set $GITHUB_TOKEN, or use "
            "--offline-store for offline testing",
            EXIT_USAGE_ERROR,
        )
    return GitHubBackend(args.repo, token)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        backend = make_backend(args)
        if args.command == "claim":
            session_id = args.session_id or f"session-{uuid.uuid4().hex[:8]}"
            return claim(backend, args.issue, args.label, session_id, args.dry_run)
        elif args.command == "verify-refs":
            refs = parse_refs(args)
            return verify_refs(backend, refs, args.any_state)
        else:  # pragma: no cover - argparse enforces valid subcommands
            parser.error(f"unknown command: {args.command}")
            return EXIT_USAGE_ERROR
    except TrackerError as exc:
        emit("error", reason=str(exc))
        return exc.exit_code
    except OSError as exc:
        emit("error", reason=f"could not read/write file: {exc}")
        return EXIT_USAGE_ERROR


if __name__ == "__main__":
    sys.exit(main())
