"""converge hub -> Tasks app: each pending recipe becomes a chain in project "Computers", closed when its check passes.

Opt-in: `hub.py serve --tasks URL` or CONVERGE_TASKS=URL (the Tasks server, e.g. http://100.73.70.25:8767). Runs in a
background thread after every stored report, so a check-in returns at once; failures go to stderr and never reach the
request. A task is matched by its exact title, `🖥 <host> · <recipe title>`, so the hub keeps no task ids of its own.
"""
from __future__ import annotations

import http.client
import json
import sys
import threading
import urllib.request
from typing import Any, List, Optional, Tuple

PROJECT = {'name': 'Computers', 'emoji': '🖥', 'color': 'sapphire'}  # created on first use
PRIORITY = 3  # optional in Joe's scheme: a login can wait for a quiet moment
TIMEOUT_S = 20
STEP_WORDS = 6  # Joe's chain format: step titles of at most six words, starting with the verb
FILLER = {'a', 'all', 'an', 'and', 'any', 'at', 'by', 'each', 'every', 'for', 'from', 'in', 'it', 'its', 'of', 'on', 'or', 'the', 'then', 'this', 'to', 'with', 'your'}
LOCK = threading.Lock()  # one sync at a time: two quick reports from a host must not both create its chain


def task_title(host: str, recipe: dict) -> str:
    """The chain's title, which is also how a later report finds it again."""
    return '🖥 %s · %s' % (host, recipe['title'])


def step_title(step: str) -> str:
    """A step line cut to at most six words: before a flag, a parenthesis or a quote it cannot close, after a clause's
    comma, never on trailing filler."""
    words: List[str] = []
    for word in step.split()[:STEP_WORDS]:
        if words and starts_an_aside(word):
            break
        words.append(word)
        if word.endswith((',', ';')):
            break
    while len(words) > 1 and is_dangling(words[-1]):
        words.pop()
    words[-1] = words[-1].rstrip(',;:.')
    return ' '.join(words)


def starts_an_aside(word: str) -> bool:
    """A word a title stops before: a flag (`--web`), a parenthesis, or an opening quote that closes later."""
    return word.startswith(('-', '(')) or word.count('"') % 2 == 1


def is_dangling(word: str) -> bool:
    """A word a cut title must not end on: a filler word or bare punctuation such as `>`."""
    return word.lower().rstrip(',;:.') in FILLER or not any(c.isalnum() for c in word)


def chain_steps(steps: List[str]) -> List[dict]:
    """Tasks chain steps: the short title, and the full step line as the note (the exact how-to)."""
    return [{'title': step_title(step), 'done': False, 'due': None, 'wait': False, 'note': step} for step in steps]


def plan_sync(pending_titles: List[str], open_tasks: List[dict]) -> Tuple[List[str], List[dict]]:
    """(titles to create, tasks to complete) given this host's pending titles now and its open tasks."""
    open_titles = {task['title'] for task in open_tasks}
    to_create = [title for title in pending_titles if title not in open_titles]
    to_complete = [task for task in open_tasks if task['title'] not in pending_titles]
    return to_create, to_complete


# --- the Tasks API --------------------------------------------------------------------------------------------------

def call(base: str, path: str, body: Optional[dict] = None) -> Any:
    """Decoded JSON answer of a GET, or of a POST of `body`; OSError/HTTPException/ValueError when it fails."""
    data = None if body is None else json.dumps(body).encode()
    asked = urllib.request.Request(base.rstrip('/') + path, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(asked, timeout=TIMEOUT_S) as answer:
        return json.loads(answer.read() or b'null')


def project_id(base: str) -> int:
    """Id of project Computers, created when absent (GET /api/projects lists archived ones too, so none is doubled)."""
    for project in call(base, '/api/projects'):
        if project['name'] == PROJECT['name']:
            return project['id']
    return call(base, '/api/projects', PROJECT)['id']


def create(base: str, title: str, recipe: dict, project: int) -> None:
    """One chain task for a pending recipe."""
    call(base, '/api/tasks', {'title': title, 'project_id': project, 'priority': PRIORITY, 'chain': chain_steps(recipe['steps']),
                              'description': 'converge recipe %s; closes itself when a later check-in passes' % recipe['name']})


def complete(base: str, task: dict) -> None:
    """Finish a task: /done ticks one chain step at a time, so it is called once per step left (once for a plain task)."""
    steps_left = len(task.get('chain') or []) - max(task.get('cur', -1), 0)
    for _ in range(max(steps_left, 1)):
        call(base, '/api/tasks/%d/done' % task['id'], {})


def sync_host(base: str, host: str, pending: List[dict]) -> Tuple[int, int]:
    """Make the open `🖥 <host> · ...` tasks match this host's pending recipes; (created, completed)."""
    prefix = '🖥 %s · ' % host
    open_tasks = [task for task in call(base, '/api/state')['tasks'] if task['title'].startswith(prefix)]
    by_title = {task_title(host, recipe): recipe for recipe in pending}
    to_create, to_complete = plan_sync(list(by_title), open_tasks)
    project = project_id(base) if to_create else 0
    for title in to_create:
        create(base, title, by_title[title], project)
    for task in to_complete:
        complete(base, task)
    return len(to_create), len(to_complete)


def guarded_sync(base: str, host: str, pending: List[dict]) -> None:
    """sync_host one at a time, any failure logged to stderr instead of raised."""
    with LOCK:
        try:
            sync_host(base, host, pending)
        except (OSError, http.client.HTTPException, ValueError, KeyError, TypeError) as exc:
            print('tasks: %s: %s' % (host, exc), file=sys.stderr, flush=True)


def file_in_background(base: Optional[str], last: dict) -> Optional[threading.Thread]:
    """After a stored report: sync that host's tasks in a daemon thread (the thread, for tests), or nothing when off."""
    if not base:
        return None
    host = last['machine'].split('@', 1)[1]
    worker = threading.Thread(target=guarded_sync, args=(base, host, last.get('pending') or []), daemon=True)
    worker.start()
    return worker
