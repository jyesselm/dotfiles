#!/usr/bin/env bash
# autonomy-guard.sh — enforced PreToolUse denylist for unattended Claude Code runs.
#
# Active ONLY during autonomous runs — i.e. only while ~/.claude/.autonomous-active
# exists. Outside an /autopilot run the guard is a complete no-op and never interferes
# with normal interactive work. When armed it fires regardless of permission mode, so it
# still guards under skipDangerousModePermissionPrompt. Denylist (armed only):
#   - destroying/overwriting a protected/ground-truth path (protected-paths.txt)
#   - force/mirror pushes, and pushing the main/master branch
#   - sudo, package install/remove, broad `rm -rf`, history-rewriting git ops,
#     external comms (mail, curl/wget POST)
#
# /autopilot creates ~/.claude/.autonomous-active at start and removes it on exit.
# If a run dies and the sentinel lingers (guard stays armed), just:
#     rm ~/.claude/.autonomous-active
#
# Contract: emits PreToolUse JSON {permissionDecision: deny, ...} to block, prints
# nothing to allow. Fail-open on any internal error — a guard must not brick the session.

INPUT="$(cat)"

PYSCRIPT="$(cat <<'PY'
import json, sys, os, re, fnmatch, subprocess

def allow():
    sys.exit(0)

def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)

try:
    data = json.load(sys.stdin)
except Exception:
    allow()

tool = data.get("tool_name", "")
ti = data.get("tool_input", {}) or {}
cwd = data.get("cwd") or os.getcwd()
AUTONOMOUS = os.path.exists(os.path.expanduser("~/.claude/.autonomous-active"))

# The guard is armed ONLY during an autonomous run. Outside one, allow everything.
if not AUTONOMOUS:
    allow()

def protected_globs():
    out = []
    try:
        with open(os.path.expanduser("~/.claude/protected-paths.txt")) as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#"):
                    out.append(s)
    except FileNotFoundError:
        pass
    return out

def is_protected(path):
    if not path:
        return False
    p = os.path.abspath(os.path.expanduser(path))
    base = os.path.basename(p)
    for g in protected_globs():
        gx = os.path.expanduser(g)
        if "**" in gx:
            prefix = gx.split("**")[0].rstrip("/")
            if prefix and prefix in p:
                return True
        if fnmatch.fnmatch(p, gx) or fnmatch.fnmatch(base, g):
            return True
        if gx.endswith("/") and gx.rstrip("/") in p:
            return True
    return False

# ---- file-writing tools ----
if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
    path = ti.get("file_path") or ti.get("notebook_path") or ""
    if is_protected(path):
        deny("autonomy-guard: %s is a protected/ground-truth path "
             "(~/.claude/protected-paths.txt). Write derived output to a separate path; "
             "editing this requires human approval." % path)
    allow()

# ---- Bash ----
if tool == "Bash":
    cmd = ti.get("command", "") or ""

    # destructive verb touching a protected path
    if re.search(r'\b(rm|mv|cp|dd|truncate|shred|tee)\b', cmd) or re.search(r'>\s*[^\s|]', cmd):
        for tok in re.findall(r"[^\s'\";|&><]+", cmd):
            if is_protected(tok):
                deny("autonomy-guard: command would modify or delete protected path %s." % tok)

    # force / main-branch pushes
    if re.search(r'\bgit\b[^\n]*\bpush\b', cmd):
        if re.search(r'(--force(-with-lease)?\b|(?<!\w)-f\b|--mirror\b)', cmd):
            deny("autonomy-guard: force/mirror push is hard-stopped; needs human approval.")
        if re.search(r'\bpush\b[^\n]*\b(main|master)\b', cmd):
            deny("autonomy-guard: pushing main/master is hard-stopped. Use a work branch.")
        try:
            br = subprocess.run(["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            br = ""
        if br in ("main", "master"):
            deny("autonomy-guard: current branch is %s; refusing to push it unattended. "
                 "Work on a dedicated branch." % br)

    # denylist (armed only — see early return above)
    rules = [
        (r'\bsudo\b', "sudo"),
        (r'\b(pip3?|conda|mamba|micromamba|npm|yarn|pnpm|brew|apt|apt-get|cargo|gem|uv)\s+'
         r'(install|add|i|remove|uninstall)\b', "package install/remove"),
        (r'\brm\s+-[a-zA-Z]*r[a-zA-Z]*f|\brm\s+-[a-zA-Z]*f[a-zA-Z]*r', "rm -rf"),
        (r'\bgit\s+reset\s+--hard\b', "git reset --hard"),
        (r'\bgit\s+clean\s+-[a-zA-Z]*[df]', "git clean -fd"),
        (r'\bgit\s+filter-(branch|repo)\b', "git history rewrite"),
        (r'\bgit\s+push\b[^\n]*--delete\b', "git delete remote ref"),
        (r'\b(mail|mailx|sendmail|msmtp)\b', "sending mail"),
        (r'\bcurl\b[^\n]*(-X\s*(POST|PUT|DELETE|PATCH)|--data\b|--data-\w+|'
         r'(?<!\w)-d\b|(?<!\w)-F\b|--upload-file)', "curl sending data externally"),
        (r'\bwget\b[^\n]*(--post-data|--post-file|--method=(POST|PUT|DELETE))', "wget POST"),
    ]
    for pat, label in rules:
        if re.search(pat, cmd):
            deny("autonomy-guard [autonomous mode]: '%s' is on the hard-stop denylist. "
                 "Record it in NEEDS_HUMAN.md and wait for approval instead." % label)

allow()
PY
)"

printf '%s' "$INPUT" | python3 -c "$PYSCRIPT"
