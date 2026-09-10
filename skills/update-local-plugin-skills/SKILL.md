---
name: update-local-plugin-skills
description: Use when asked to "update local plugin skills", "pull plugin skills", "sync plugin skills to OpenCode", "rsync skills to .opencode", or refresh skills from a locally checked-out plugin repository.
---

# Update Local Plugin Skills

Refresh skills from a locally checked-out plugin without leaving obsolete skills behind or deleting skills managed by another plugin.

## Collect Inputs

Require all of the following before running a destructive sync:

- Plugin repository: the existing local Git checkout.
- Skills source: normally `<plugin-repo>/skills`.
- Plugin name: a stable directory name used to isolate this plugin's installed skills.
- Scope: `user` or `project`.

Accept `PLUGIN_NAME` only when it matches `^[a-z0-9][a-z0-9-]*$`. Reject path components, `.` and `..` so the destination remains a direct child of the plugin skills directory.

Use these OpenCode roots:

| Scope | Root |
| --- | --- |
| User | `${XDG_CONFIG_HOME:-$HOME/.config}/opencode` |
| Project | `<project-root>/.opencode` |

Install each plugin below `<root>/skills/<plugin-name>/`. Do not sync directly into `<root>/skills/`: `--delete` must only remove content that this plugin owns.

Run this workflow in a POSIX shell with Git and `rsync` available. Use WSL or an equivalent POSIX environment on Windows.

Treat the checkout as trusted. `-L` deliberately follows every source symlink; do not use this workflow on an untrusted repository.

## Update Workflow

1. Derive the OpenCode root from the selected scope. Require an explicit absolute project root instead of inferring it from the current directory:

   ```bash
   case "$SCOPE" in
     user ) OPENCODE_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/opencode" ;;
     project )
       test -n "$PROJECT_ROOT" && test -d "$PROJECT_ROOT" || exit 1
       case "$PROJECT_ROOT" in /* ) ;; * ) exit 1 ;; esac
       OPENCODE_ROOT="$PROJECT_ROOT/.opencode"
       ;;
     * ) exit 1 ;;
   esac
   ```

2. Verify that the repository is a Git checkout, that its skills source exists, and that the plugin name is valid:

   ```bash
   git -C "$PLUGIN_REPO" rev-parse --is-inside-work-tree >/dev/null || exit 1
   test -d "$PLUGIN_REPO/skills" || exit 1
   LC_ALL=C
   export LC_ALL
   case "$PLUGIN_NAME" in
     [a-z0-9]* ) case "$PLUGIN_NAME" in *[!a-z0-9-]* ) exit 1 ;; esac ;;
     * ) exit 1 ;;
   esac
   ```
3. Pull the checkout with fast-forward-only history:

   ```bash
   git -C "$PLUGIN_REPO" pull --ff-only
   ```

4. Stop if the pull fails. Do not sync from an unknown repository state.
5. Create the plugin-scoped destination and synchronize only after the pull succeeds. Reject symlinks at the destination or below it before `rsync --delete` can follow them:

   ```bash
   DEST="$OPENCODE_ROOT/skills/$PLUGIN_NAME"
   test ! -e "$DEST" || test -d "$DEST" || { printf 'Destination is not a directory: %s\n' "$DEST" >&2; exit 1; }
   test ! -L "$DEST" || { printf 'Refusing symlinked destination: %s\n' "$DEST" >&2; exit 1; }
   if test -d "$DEST" && find "$DEST" -type l -print -quit | grep -q .; then
     printf 'Refusing destination containing symlinks: %s\n' "$DEST" >&2
     exit 1
   fi
   mkdir -p "$DEST"
   rsync -aL --delete "$PLUGIN_REPO/skills/" "$DEST/"
   ```

Use `-L` so symlinked skill files are copied as their real contents. Use `--delete` only with the plugin-scoped destination so removed upstream skills disappear without affecting other installed plugins.

## Complete Example

Update the `example-plugin` checkout for the explicit project root `/work/app`:

```bash
PLUGIN_REPO="$HOME/Code/example-plugin"
PLUGIN_NAME="example-plugin"
SCOPE="project"
PROJECT_ROOT="/work/app"

case "$SCOPE" in
  user ) OPENCODE_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/opencode" ;;
  project )
    test -n "$PROJECT_ROOT" && test -d "$PROJECT_ROOT" || exit 1
    case "$PROJECT_ROOT" in /* ) ;; * ) exit 1 ;; esac
    OPENCODE_ROOT="$PROJECT_ROOT/.opencode"
    ;;
  * ) exit 1 ;;
esac

git -C "$PLUGIN_REPO" rev-parse --is-inside-work-tree >/dev/null || { printf 'Not a Git checkout: %s\n' "$PLUGIN_REPO" >&2; exit 1; }
test -d "$PLUGIN_REPO/skills" || { printf 'Missing skills directory: %s/skills\n' "$PLUGIN_REPO" >&2; exit 1; }
LC_ALL=C
export LC_ALL
case "$PLUGIN_NAME" in
  [a-z0-9]* ) case "$PLUGIN_NAME" in *[!a-z0-9-]* ) printf 'Invalid plugin name: %s\n' "$PLUGIN_NAME" >&2; exit 1 ;; esac ;;
  * ) printf 'Invalid plugin name: %s\n' "$PLUGIN_NAME" >&2; exit 1 ;;
esac
git -C "$PLUGIN_REPO" pull --ff-only || exit $?

DEST="$OPENCODE_ROOT/skills/$PLUGIN_NAME"
test ! -e "$DEST" || test -d "$DEST" || { printf 'Destination is not a directory: %s\n' "$DEST" >&2; exit 1; }
test ! -L "$DEST" || { printf 'Refusing symlinked destination: %s\n' "$DEST" >&2; exit 1; }
if test -d "$DEST" && find "$DEST" -type l -print -quit | grep -q .; then
  printf 'Refusing destination containing symlinks: %s\n' "$DEST" >&2
  exit 1
fi
mkdir -p "$DEST"
rsync -aL --delete "$PLUGIN_REPO/skills/" "$DEST/"
```

Report the repository, source directory, destination, and whether the pull and sync completed. Restart OpenCode after the update; it loads skills at startup.

## Common Mistakes

- Omitting `-L`: symlinked skill content may not be copied into the install.
- Syncing into the shared `skills/` directory: `--delete` can remove another plugin's skills.
- Running `rsync` after a failed pull: installs from an unverified checkout state.
- Reusing a destination symlink: `--delete` could affect content outside this plugin's directory.
- Trusting an unknown checkout: `-L` follows its source symlinks.
- Deriving a project root from the current directory: nested shells can install into the wrong project scope.
- Using `~/.opencode`: user-level OpenCode configuration belongs in `~/.config/opencode` by default.
