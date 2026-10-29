"""Recipes: the manual steps converge cannot take itself (logins, permissions, App Store, sudo), each with a check.

setup/recipes.txt holds the records; a recipe is pending on a machine when any of its checks fails against that
machine's snapshot (state.json keys) plus `phase.<key>` = each sync phase's status. `evaluate` is pure, so the sync,
`converge status` and the hub all decide the same way.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sync import STATE_DIR, PhaseResult, age

RECIPES_FILE = 'recipes.txt'
KEYS = ('recipe', 'title', 'on', 'check', 'step')
REPEATED = ('check', 'step')
VALUE_OPS = ('==', '!=', '<', '>', 'has')
BARE_OPS = ('empty', 'present')
UNITS = {'m': 1 / 60, 'h': 1, 'd': 24, 'w': 168}  # in hours: `atuin.synced < 24h` and `< 1d` mean the same
ABSENT = 'absent'  # what a key this machine does not have looks like to a check


@dataclass
class Recipe:
    """One record of recipes.txt."""
    name: str
    title: str = ''
    on: List[str] = field(default_factory=list)  # profiles and/or classes; empty means every machine
    checks: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)


@dataclass
class Pending:
    """A recipe whose check failed here, as last.json and the hub store it."""
    name: str
    title: str
    steps: List[str]


# --- parsing --------------------------------------------------------------------------------------------------------

def parse(text: str) -> List[Recipe]:
    """Records separated by blank lines, `key: value` lines, `check:` and `step:` repeated, full-line `#` comments.
    ValueError names the line of anything malformed (unknown key, bad check, a record without title or step)."""
    recipes: List[Recipe] = []
    record: Dict[str, List[str]] = {}
    start = 0
    for number, raw in enumerate(text.splitlines() + [''], 1):  # the extra blank line closes the last record
        line = raw.strip()
        if line.startswith('#'):
            continue
        if not line:
            if record:
                recipes.append(_recipe(start, record))
            record = {}
            continue
        key, colon, value = line.partition(':')
        if not colon or key.strip() not in KEYS or not value.strip():
            raise ValueError('%s line %d: expected `key: value` with key %s' % (RECIPES_FILE, number, '|'.join(KEYS)))
        start = start if record else number
        record.setdefault(key.strip(), []).append(value.strip())
    _unique([r.name for r in recipes])
    return recipes


def _recipe(number: int, record: Dict[str, List[str]]) -> Recipe:
    """A validated Recipe from one record's key -> values."""
    where = '%s line %d' % (RECIPES_FILE, number)
    for key in ('recipe', 'title', 'step'):
        if key not in record:
            raise ValueError('%s: record without %s:' % (where, key))
    single = [k for k, values in record.items() if len(values) > 1 and k not in REPEATED]
    if single:
        raise ValueError('%s: %s: given twice' % (where, single[0]))
    for check in record.get('check', []):
        parse_check(check, where)
    on = [part.strip() for part in record.get('on', [''])[0].split(',') if part.strip()]
    return Recipe(record['recipe'][0], record['title'][0], on, record.get('check', []), record['step'])


def _unique(names: List[str]) -> None:
    """ValueError for a recipe name used twice."""
    seen = set()
    for name in names:
        if name in seen:
            raise ValueError('%s: recipe %s defined twice' % (RECIPES_FILE, name))
        seen.add(name)


def parse_check(check: str, where: str = RECIPES_FILE) -> Tuple[str, str, str]:
    """(key, op, value) of `<key> <op> [value]`; ValueError for an unknown op or a missing/extra value."""
    parts = check.split(None, 2)
    key, op, value = (parts + ['', ''])[:3]
    takes_value = op in VALUE_OPS
    if op not in VALUE_OPS + BARE_OPS or takes_value != bool(value):
        raise ValueError('%s: bad check %r (ops: %s take a value; %s do not)' % (where, check, ' '.join(VALUE_OPS), ' '.join(BARE_OPS)))
    return key, op, value


def load(path: Path) -> List[Recipe]:
    """The recipes in a file; none when it is absent."""
    return parse(path.read_text()) if path.exists() else []


# --- evaluation -----------------------------------------------------------------------------------------------------

def hours(value: object) -> Optional[float]:
    """A number, or a duration like 30m, 24h, 1d, 2w in hours; None when it is neither."""
    text, unit = str(value).strip(), 1.0
    if text[-1:].isalpha():
        if text[-1] not in UNITS:
            return None
        text, unit = text[:-1], UNITS[text[-1]]
    try:
        return float(text) * unit
    except ValueError:
        return None


def passes(check: str, lookup: Dict[str, object]) -> bool:
    """Whether one check holds. A list value matches == when any element does (and != when none does); < and >
    compare numbers or durations; `has` needs the item in a list; `empty` an empty list; `present` any value but absent."""
    key, op, expected = parse_check(check)
    value = lookup.get(key, ABSENT)
    if op == 'present':
        return value != ABSENT
    if op == 'empty':
        return value == [] or value == ''
    if op in ('==', '!='):
        found = expected in value if isinstance(value, list) else str(value) == expected
        return found if op == '==' else not found
    if op == 'has':
        return isinstance(value, list) and expected in value
    return _compare_numbers(op, hours(value), hours(expected))


def _compare_numbers(op: str, value: Optional[float], limit: Optional[float]) -> bool:
    """value < limit or value > limit; False when either is not a number."""
    if value is None or limit is None:
        return False
    return value < limit if op == '<' else value > limit


def applies(recipe: Recipe, profile: str, machine_class: str) -> bool:
    """A recipe with no `on:` applies everywhere; otherwise this machine's profile or class must be listed."""
    return not recipe.on or profile in recipe.on or machine_class in recipe.on


def evaluate(recipes: List[Recipe], lookup: Dict[str, object], profile: str, machine_class: str) -> List[Pending]:
    """The recipes that apply here and have a failing check, in file order."""
    return [Pending(r.name, r.title, r.steps) for r in recipes
            if applies(r, profile, machine_class) and not all(passes(c, lookup) for c in r.checks)]


# --- the sync phase and the CLI -------------------------------------------------------------------------------------

def phase(setup, state: Dict[str, object], statuses: Dict[str, str]) -> Tuple[PhaseResult, List[Pending]]:
    """(phase result, pending recipes) from this run's snapshot and phase statuses, plus declared.py's generated ones."""
    import declared
    lookup = dict(state)
    lookup.update({'phase.' + key: status for key, status in statuses.items()})
    found = evaluate(load(setup.assets / RECIPES_FILE), lookup, setup.profile, setup.machine_class())
    found += declared.pending(setup, state)
    if not found:
        return PhaseResult('ok', 'nothing pending'), []
    details = ['%s: %s' % (p.title, p.steps[0]) for p in found]
    return PhaseResult('warn', '%d pending; converge status lists their steps' % len(found), details), found


def pending_lines(pending: List[dict]) -> List[str]:
    """Each pending recipe as a title line and numbered steps (converge status, converge recipes)."""
    lines = []
    for recipe in pending:
        lines.append('\n  %s  (converge recipe %s)' % (recipe['title'], recipe['name']))
        lines += ['    %d. %s' % (number, step) for number, step in enumerate(recipe['steps'], 1)]
    return lines


def show(setup, name: Optional[str]) -> int:
    """`converge recipes` (no name): the pending recipes of the last sync; `converge recipe NAME`: one recipe's steps."""
    path = setup.root / STATE_DIR / 'last.json'
    last = json.loads(path.read_text()) if path.exists() else {}
    pending = last.get('pending', [])
    if name is None:
        if not pending:
            setup.say('Nothing pending%s' % (' (last sync %s)' % age(last['finished']) if last else '; no sync has run yet'))
            return 0
        setup.say('\n'.join(pending_lines(pending)).lstrip('\n'))
        return 0
    known = {r['name']: r for r in pending}
    known.update({r.name: {'name': r.name, 'title': r.title, 'steps': r.steps} for r in load(setup.assets / RECIPES_FILE)})
    if name not in known:
        setup.say('No recipe %s; known: %s' % (name, ', '.join(sorted(known))))
        return 1
    setup.say('\n'.join(pending_lines([known[name]])).lstrip('\n'))
    return 0
