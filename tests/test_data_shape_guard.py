import os, subprocess, tempfile, unittest
from pathlib import Path
from data_shape_guard import infer, compare, load_records, should_fail

class T(unittest.TestCase):
    def test_type_and_required_drift(self):
        a = infer([{'id':1,'name':'a'},{'id':2,'name':'b'}])
        b = infer([{'id':'1'},{'id':'2','name':'b'}])
        changes = compare(a,b)
        text = ' | '.join(x['change'] for x in changes)
        self.assertIn('types', text)
        self.assertIn('required', text)

    def test_required_drift_threshold_is_configurable(self):
        a = infer([{'x':1},{'x':2},{'x':3},{'x':4}])
        b = infer([{'x':1},{'x':2},{'x':3},{}])
        self.assertFalse(any('required' in x['change'] for x in compare(a,b,.30)))
        self.assertTrue(any('required' in x['change'] for x in compare(a,b,.20)))
        with self.assertRaisesRegex(ValueError, 'between 0 and 1'):
            compare(a,b,1.1)

    def test_failure_policy_respects_severity(self):
        changes = [
            {'path':'$.new','change':'added','severity':'info'},
            {'path':'$.optional','change':'required 100% → 50%','severity':'medium'},
        ]
        self.assertFalse(should_fail(changes,'never'))
        self.assertFalse(should_fail(changes,'high'))
        self.assertTrue(should_fail(changes,'medium'))
        self.assertTrue(should_fail(changes,'any'))

    def test_secret_named_path_redacts_examples(self):
        shape = infer([{'api_key':'abc123456789','name':'safe'}])
        self.assertEqual(shape['paths']['$.api_key']['examples'], ['<redacted>'])
        self.assertEqual(shape['paths']['$.name']['examples'], ['safe'])

    def test_bracketed_secret_like_keys_redact_examples(self):
        shape = infer([{'api key':'abc123456789','auth token':'token-value','safe label':'visible'}])
        self.assertEqual(shape['paths']['$["api key"]']['examples'], ['<redacted>'])
        self.assertEqual(shape['paths']['$["auth token"]']['examples'], ['<redacted>'])
        self.assertEqual(shape['paths']['$["safe label"]']['examples'], ['visible'])

class ArrayCoverageTests(unittest.TestCase):
    def test_type_change_after_first_50_array_items_is_detected(self):
        baseline = infer([{'items':[1]*51}])
        current = infer([{'items':[1]*50+['late-string']}])
        self.assertEqual(current['paths']['$.items[]']['types'], {'int':50, 'string':1})
        changes = compare(baseline,current)
        self.assertTrue(any(x['path']=='$.items[]' and x['severity']=='high' and 'types' in x['change'] for x in changes))

class PathCollisionTests(unittest.TestCase):
    def test_literal_dot_key_does_not_collide_with_nested_path(self):
        shape = infer([{'a.b':1,'a':{'b':'nested'}}])
        self.assertIn('$.a.b', shape['paths'])
        self.assertIn('$["a.b"]', shape['paths'])
        self.assertEqual(shape['paths']['$.a.b']['types'], {'string':1})
        self.assertEqual(shape['paths']['$["a.b"]']['types'], {'int':1})

    def test_literal_array_marker_key_does_not_collide_with_array_path(self):
        shape = infer([{'items[]':'literal','items':[2]}])
        self.assertIn('$.items[]', shape['paths'])
        self.assertIn('$["items[]"]', shape['paths'])
        self.assertEqual(shape['paths']['$.items[]']['types'], {'int':1})
        self.assertEqual(shape['paths']['$["items[]"]']['types'], {'string':1})

class StrictJsonTests(unittest.TestCase):
    def test_nonfinite_json_constants_are_rejected(self):
        base = Path(tempfile.mkdtemp())
        cases = [
            ('nan.json', '[{"x":NaN}]', 'non-finite JSON number'),
            ('inf.json', '[{"x":Infinity}]', 'non-finite JSON number'),
            ('neg-inf.jsonl', '{"x":-Infinity}\n', 'line 1: non-finite JSON number'),
        ]
        for name, text, message in cases:
            p = base / name; p.write_text(text)
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, message):
                    load_records(p)

    def test_cli_fails_before_writing_reports_for_nonfinite_json(self):
        base = Path(tempfile.mkdtemp())
        src = base / 'bad.json'; src.write_text('[{"x":NaN}]')
        json_out = base / 'shape.json'; html_out = base / 'shape.html'
        cp = subprocess.run([os.sys.executable, 'data_shape_guard.py', 'infer', str(src), '--json', str(json_out), '--html', str(html_out)], text=True, capture_output=True)
        self.assertEqual(cp.returncode, 2)
        self.assertIn('non-finite JSON number', cp.stderr)
        self.assertFalse(json_out.exists()); self.assertFalse(html_out.exists())

    def test_cli_ci_gate_writes_reports_then_fails_on_high(self):
        base = Path(tempfile.mkdtemp())
        before = base / 'before.json'; after = base / 'after.json'
        before.write_text('[{"id":1}]'); after.write_text('[{"id":"1"}]')
        json_out = base / 'drift.json'; html_out = base / 'drift.html'
        cp = subprocess.run([
            os.sys.executable, 'data_shape_guard.py', 'compare', str(before), str(after),
            '--fail-on', 'high', '--json', str(json_out), '--html', str(html_out)
        ], text=True, capture_output=True)
        self.assertEqual(cp.returncode, 1)
        self.assertTrue(json_out.exists()); self.assertTrue(html_out.exists())
        self.assertIn('drift=', cp.stdout)

    def test_cli_default_remains_report_only(self):
        base = Path(tempfile.mkdtemp())
        before = base / 'before.json'; after = base / 'after.json'
        before.write_text('[{"id":1}]'); after.write_text('[{"id":"1"}]')
        cp = subprocess.run([os.sys.executable, 'data_shape_guard.py', 'compare', str(before), str(after)], cwd='.', text=True, capture_output=True)
        self.assertEqual(cp.returncode, 0)
