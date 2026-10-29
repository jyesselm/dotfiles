"""Recipes (recipes.py): the grammar, every check op, evaluation, the sync phase and `converge recipe(s)`; no real commands."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

import declared as dc
import recipes as rc
import sync as sy

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('bootstrap_setup', HERE / 'setup.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

SLUGS = ('gh-login', 'atuin-sync', 'op-signin', 'tailscale-up', 'ssh-keys', 'keychain-secrets', 'karabiner-input-monitoring',
         'layout', 'hotkeys-clash', 'brew-extras', 'dotfiles-pull', 'repos-fix', 'doctor-checks')
SAMPLE = '''# comment
recipe: one
title: First
check: a.b == yes
step: do it
step: then this

recipe: two
title: Second
on: mac, studio
check: n < 2h
step: x
'''


class GrammarTests(unittest.TestCase):
    def test_records_on_lists_and_repeated_keys(self):
        one, two = rc.parse(SAMPLE)
        self.assertEqual((one.name, one.title, one.on, one.checks, one.steps), ('one', 'First', [], ['a.b == yes'], ['do it', 'then this']))
        self.assertEqual((two.on, two.checks), (['mac', 'studio'], ['n < 2h']))
        self.assertEqual(rc.parse(''), [])

    def test_malformed_records_name_the_line(self):
        cases = [('recipe: x\ncolour: red\n', 'line 2: expected `key: value`'),
                 ('recipe: x\ntitle: T\n', 'line 1: record without step:'),
                 ('\n\nrecipe: x\ntitle: T\ntitle: U\nstep: s\n', 'line 3: title: given twice'),
                 ('recipe: x\ntitle: T\ncheck: a ~ b\nstep: s\n', "bad check 'a ~ b'"),
                 ('recipe: x\ntitle: T\ncheck: a empty b\nstep: s\n', 'bad check'),
                 ('recipe: x\ntitle: T\ncheck: a ==\nstep: s\n', 'bad check'),
                 ('recipe: x\ntitle: T\nstep: s\n\nrecipe: x\ntitle: U\nstep: s\n', 'recipe x defined twice')]
        for text, message in cases:
            with self.assertRaisesRegex(ValueError, message):
                rc.parse(text)

    def test_the_real_file_parses_with_the_planned_slugs(self):
        names = [r.name for r in rc.load(HERE / rc.RECIPES_FILE)]
        for slug in SLUGS:
            self.assertIn(slug, names)
        self.assertEqual(rc.load(HERE / 'no-such-file.txt'), [])


class CheckTests(unittest.TestCase):
    lookup = {'s': 'yes', 'l': ['a', 'b'], 'e': [], 'n': 23.9, 'phase.layout': 'ok', 'bad': 'error: x'}

    def test_every_op(self):
        cases = [('s == yes', True), ('s != yes', False), ('l == a', True), ('l != c', True), ('l != a', False),
                 ('n < 24h', True), ('n < 1d', True), ('n > 30m', True), ('n < 2w', True), ('n > 1d', False),
                 ('l has b', True), ('s has y', False), ('e empty', True), ('l empty', False), ('s present', True),
                 ('gone present', False), ('gone == absent', True), ('gone < 24h', False), ('bad < 24h', False),
                 ('n < 3x', False), ('phase.layout != warn', True)]
        for check, expected in cases:
            self.assertEqual(rc.passes(check, self.lookup), expected, check)
        self.assertEqual((rc.hours('90m'), rc.hours('2'), rc.hours(''), rc.hours('h')), (1.5, 2.0, None, None))

    def test_evaluate_filters_by_profile_or_class_and_keeps_file_order(self):
        recipes = rc.parse(SAMPLE)
        self.assertEqual([p.name for p in rc.evaluate(recipes, {'n': 5}, 'mac', 'laptop')], ['one', 'two'])
        self.assertEqual([p.name for p in rc.evaluate(recipes, {'n': 5}, 'linux', 'studio')], ['one', 'two'])
        self.assertEqual(rc.evaluate(recipes, {'a.b': 'yes', 'n': 5}, 'linux', 'linux'), [])
        self.assertEqual(rc.evaluate(recipes, {'a.b': 'yes', 'n': 1}, 'mac', 'laptop'), [])


class PhaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.assets = self.root / 'assets'
        (self.assets / dc.DECLARED_DIR).mkdir(parents=True)
        (self.assets / rc.RECIPES_FILE).write_text(SAMPLE)
        self.output = io.StringIO()
        self.quiet = contextlib.redirect_stdout(self.output)
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def setup(self):
        setup = m.Setup(m.parse(['sync', '--profile', 'mac']), root=self.root, assets=self.assets)
        setup._class = 'studio'
        return setup

    def last(self, pending):
        (self.root / sy.STATE_DIR).mkdir(parents=True, exist_ok=True)
        (self.root / sy.STATE_DIR / 'last.json').write_text(json.dumps({'finished': '2026-10-28T08:00:00+00:00', 'pending': pending}))

    def test_phase_adds_phase_statuses_and_generated_recipes(self):
        (self.assets / dc.DECLARED_DIR / 'apps.txt').write_text('Magnet  source:mas\n')
        state = {'a.b': 'no', 'n': 1, 'declared.apps.missing': ['Magnet']}
        result, found = rc.phase(self.setup(), state, {'layout': 'warn'})
        self.assertEqual([p.name for p in found], ['one', 'install-apps-magnet'])
        self.assertEqual((result.status, result.summary), ('warn', '2 pending; converge status lists their steps'))
        self.assertEqual(result.details, ['First: do it', 'Install Magnet (apps): App Store: search "Magnet"'])
        result, found = rc.phase(self.setup(), {'a.b': 'yes', 'n': 1}, {})
        self.assertEqual((result.status, found), ('ok', []))

    def test_show_lists_pending_and_prints_one_recipe(self):
        setup = self.setup()
        self.assertEqual(rc.show(setup, None), 0)
        self.assertIn('Nothing pending; no sync has run yet', self.output.getvalue())
        self.last([{'name': 'install-apps-x', 'title': 'Install X (apps)', 'steps': ['App Store: search "X"', 'converge sync']}])
        self.assertEqual(rc.show(setup, None), 0)
        self.assertIn('Install X (apps)  (converge recipe install-apps-x)\n    1. App Store: search "X"\n    2. converge sync', self.output.getvalue())
        self.assertEqual(rc.show(setup, 'two'), 0)  # not pending, but in recipes.txt
        self.assertIn('Second  (converge recipe two)\n    1. x', self.output.getvalue())
        self.assertEqual(rc.show(setup, 'install-apps-x'), 0)
        self.assertEqual(rc.show(setup, 'nope'), 1)
        self.assertIn('No recipe nope; known: install-apps-x, one, two', self.output.getvalue())
        self.last([])
        rc.show(setup, None)
        self.assertIn('Nothing pending (last sync', self.output.getvalue())


if __name__ == '__main__':
    unittest.main()
