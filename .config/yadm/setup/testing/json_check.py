"""Assertions on hub JSON read from stdin, for the shell test scripts (exit 0 = holds).

    json_check.py fleet HOST [EXIT]   /fleet has a row for HOST (with that exit code)
    json_check.py keys KEY...         the object has every KEY
"""
import json
import sys


def fleet(rows: list, host: str, code: str = '') -> bool:
    """True when a row for host exists and, if code is given, its exit equals it."""
    return any(r.get('host') == host and (not code or str(r.get('exit')) == code) for r in rows)


def main(argv: list) -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError as exc:
        print('  not JSON: %s' % exc, file=sys.stderr)
        return 1
    if argv[0] == 'fleet':
        return 0 if fleet(data, *argv[1:3]) else 1
    missing = [k for k in argv[1:] if k not in data]
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
