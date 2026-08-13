#!/usr/bin/env python3
"""Generate .claude-plugin/marketplace.json from the repo's component pools.

Entries produced:
- One bundle entry per plugins/<name>/ (metadata read from its plugin.json;
  version intentionally omitted — plugin.json is authoritative).
- One micro-entry per skills/<name>/ so single skills are installable
  (source points straight at the skill directory).
- One micro-entry per agents/<name>/ (`<name>-agent`) so single agents are
  installable (dir-per-agent pool; the entry lists the agent file explicitly).

Exclusions and renames live in the constants below.

Usage:
  generate-marketplace.py           # rewrite .claude-plugin/marketplace.json
  generate-marketplace.py --check   # exit 1 if the file is not up to date (CI)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".claude-plugin" / "marketplace.json"

# Skills that only work inside their bundle (they depend on plugin-level
# scripts or hooks) and therefore get no standalone micro-entry. Both owning
# bundles are currently parked under wip/plugins/, so these stay unshipped.
BUNDLE_BOUND_SKILLS = {
    "work-object-guard",  # needs ${CLAUDE_PLUGIN_ROOT}/scripts + PreToolUse hook
    "extension-audit",  # ships a bundled CLI under scripts/
}
# Skill dirs that are not shippable skills at all.
NON_SKILL_DIRS = {"in-progress"}
# Micro-entry renames where the bare skill name collides with a bundle name.
SKILL_ENTRY_RENAMES = {}

BUNDLE_ORDER = [
    "steward",
    "docker-toolkit",
    "python-mcp-development",
    "ludus-toolkit",
    "memory-mcp",
    "superpowers",
]

MICRO_VERSION = "1.0.0"


def frontmatter_description(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        raise SystemExit(f"no frontmatter in {md_path}")
    fm = m.group(1)
    dm = re.search(r"^description:\s*(.+?)(?=\n\S|\Z)", fm, re.MULTILINE | re.DOTALL)
    if not dm:
        raise SystemExit(f"no description in {md_path}")
    raw = dm.group(1)
    first, _, rest = raw.partition("\n")
    if first.strip() in (">", ">-", ">+", "|", "|-", "|+"):
        raw = rest
    desc = " ".join(raw.split())
    if desc.startswith(('"', "'")) and desc.endswith(desc[0]) and len(desc) > 1:
        desc = desc[1:-1]
    desc = desc.replace('\\"', '"')
    if len(desc) > 200:
        cut = desc[:200]
        desc = cut[: cut.rfind(" ")].rstrip(",;:") + "…"
    return desc


def bundle_entries() -> list[dict]:
    entries = []
    names = sorted(p.name for p in (ROOT / "plugins").iterdir() if p.is_dir())
    unknown = set(names) - set(BUNDLE_ORDER)
    if unknown:
        raise SystemExit(f"bundles missing from BUNDLE_ORDER: {sorted(unknown)}")
    for name in BUNDLE_ORDER:
        if name not in names:
            continue
        manifest = json.loads((ROOT / "plugins" / name / ".claude-plugin" / "plugin.json").read_text())
        entries.append(
            {
                "name": name,
                "description": manifest["description"],
                "source": f"./plugins/{name}",
                "author": manifest.get("author", {"name": "dotKnewt"}),
            }
        )
    return entries


def skill_entries() -> list[dict]:
    entries = []
    for d in sorted((ROOT / "skills").iterdir()):
        if not d.is_dir() or d.name in NON_SKILL_DIRS or d.name in BUNDLE_BOUND_SKILLS:
            continue
        entries.append(
            {
                "name": SKILL_ENTRY_RENAMES.get(d.name, d.name),
                "description": frontmatter_description(d / "SKILL.md"),
                "version": MICRO_VERSION,
                "source": f"./skills/{d.name}",
                "strict": False,
            }
        )
    return entries


def agent_entries() -> list[dict]:
    entries = []
    for d in sorted((ROOT / "agents").iterdir()):
        if not d.is_dir():
            continue
        entries.append(
            {
                "name": f"{d.name}-agent",
                "description": frontmatter_description(d / f"{d.name}.md"),
                "version": MICRO_VERSION,
                "source": f"./agents/{d.name}",
                "strict": False,
                "agents": [f"./{d.name}.md"],
            }
        )
    return entries


def build() -> dict:
    plugins = bundle_entries() + skill_entries() + agent_entries()
    names = [p["name"] for p in plugins]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        raise SystemExit(f"duplicate entry names: {sorted(dupes)}")
    return {
        "name": "awesome-agency",
        "description": (
            "dotKnewt's Claude Code marketplace — one repo of shared skills, agents, "
            "commands, and hooks. Install curated plugin bundles or any single skill/agent."
        ),
        "owner": {"name": "dotKnewt", "email": "dotknewt@keemail.me"},
        "plugins": plugins,
    }


def main() -> int:
    rendered = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        if OUT.read_text(encoding="utf-8") != rendered:
            print("marketplace.json is stale — run .github/scripts/generate-marketplace.py", file=sys.stderr)
            return 1
        print("marketplace.json is up to date")
        return 0
    OUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUT} ({len(build()['plugins'])} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
