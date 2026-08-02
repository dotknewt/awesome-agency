# Python CLI Standards

## Toolchain

- **Dev loop:** `uv sync` / `uv run` inside the repo during
  development.
- **End-user install:** `uv tool install <pkg>` for persistent
  installs, or `uvx <pkg>` for ephemeral runs. Do not document
  pip/pipx as the primary path.

## Framework

Recommend **Typer**: type-hint-driven command definitions,
auto-generated `--help`, and built-in `--install-completion` /
`--show-completion` (no separate `argcomplete` registration step;
pairs cleanly with a `uv tool install`-first story). Click/argparse
are acceptable fallbacks for constrained cases, not the default
recommendation.

## `--help` standard

- Every command and subcommand has a one-line summary.
- Every option has help text.
- Top-level `--help` lists the subcommands.
- The app's docstring includes a usage example (Typer renders it in
  help output).

## Completion standard

The README's install section documents `<tool> --install-completion`
as a one-time per-shell setup step.
