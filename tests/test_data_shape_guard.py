import os, subprocess, tempfile, unittest
from pathlib import Path
from data_shape_guard import infer, compare, load_records

class T(unittest.TestCase):
    def test_type_and_required_drift(self):
        a = infer([{'id':1,'name':'a'},{'id':2,'name':'b'}])
        b = infer([{'id':'1'},{'id':'2','name':'b'}])
        changes = compare(a,b)
        text = ' | '.join(x['change'] for x in changes)
        self.assertIn('types', text)
        self.assertIn('required', text)

    def test_secret_named_path_redacts_examples(self):
        shape = infer([{'api_key':'abc123456789','name':'safe'}])
        self.assertEqual(shape['paths']['$.api_key']['examples'], ['<redacted>'])
        self.assertEqual(shape['paths']['$.name']['examples'], ['safe'])

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
