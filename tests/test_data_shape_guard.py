import unittest
from data_shape_guard import infer, compare

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
