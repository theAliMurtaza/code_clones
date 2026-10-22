"""Regressions reconstructed from the screenshots plus independent small cases.

These are targeted fixtures, not a population accuracy benchmark.
"""
import os
os.environ['DATABASE_URL'] = 'sqlite://'
import unittest
from unittest.mock import patch, Mock
import numpy as np

from behavior_check import probe, compare_probes
from classifier import near_miss_similarity
from detector import UploadedFile, run_detection
from graphcodebert.parser.utils import index_to_code_token

TOTAL = '''def calculate_total(prices):
    total = 0
    for price in prices:
        total += price
    return total'''
SUM = '''def sum_values(items):
    amount = 0
    for item in items:
        amount = amount + item
    return amount'''
FREQUENCY = '''def count_frequency(items):
    frequency = {}
    for item in items:
        if item in frequency:
            frequency[item] += 1
        else:
            frequency[item] = 1
    return frequency'''
FACTORIAL = '''def factorial(number):
    result = 1
    for value in range(1, number + 1):
        result *= value
    return result'''
RECURSIVE = '''def fact(n):
    if n <= 1:
        return 1
    return n * fact(n - 1)'''


class HighScoreEngine:
    supports_semantics = True
    is_fine_tuned = False
    def embed_batch(self, codes, langs):
        # Adversarially high scores: checks must still reject counterexamples.
        return np.tile([1., 0.], (len(codes), 1))


class QualityTests(unittest.TestCase):
    def test_reported_false_positives_rejected_in_all_upload_layouts(self):
        for a, b in [(FREQUENCY, SUM), (TOTAL, FACTORIAL)]:
            layouts = [[UploadedFile('single.py', a + '\n\n' + b)],
                       [UploadedFile('a.py', a), UploadedFile('b.py', b)],
                       [UploadedFile('folder/a.py', a), UploadedFile('folder/nested/b.py', b)]]
            for files in layouts:
                with self.subTest(paths=[f.filename for f in files]):
                    result = run_detection(files, 0.5, HighScoreEngine())
                    self.assertEqual(result.clone_pairs, [])
                    self.assertEqual(result.behavioral_rejections, 1)

    def test_recursive_iterative_factorial_is_retained(self):
        result = run_detection([UploadedFile('a.py', FACTORIAL), UploadedFile('b.py', RECURSIVE)],
                               0.5, HighScoreEngine())
        pair, = result.clone_pairs
        self.assertEqual(pair.clone_type, 'Type-4')
        self.assertEqual(result.behavioral_consistent, 1)
        self.assertIn('bounded Python samples agree', pair.description)
        self.assertIn('not proof', pair.description)

    def test_builtin_sum_and_loop_agree(self):
        evidence = compare_probes(probe(TOTAL), probe('def total(xs):\n    return sum(xs)'))
        self.assertEqual(evidence.status, 'consistent')
        self.assertGreaterEqual(evidence.checked, 3)

    def test_reordering_is_not_sorting(self):
        evidence = compare_probes(probe('def f(xs):\n    return xs[::-1]'),
                                  probe('def g(xs):\n    return sorted(xs)'))
        self.assertEqual(evidence.status, 'different')

    def test_matching_few_inputs_does_not_hide_later_difference(self):
        a = 'def f(x):\n    return x * x'
        b = 'def f(x):\n    return x if x <= 1 else x * x + 1'
        self.assertEqual(compare_probes(probe(a), probe(b)).status, 'different')

    def test_unsupported_code_cannot_access_host(self):
        cases = ['def f(x):\n    return open("test.txt", "w")',
                 'def f(x):\n    import os\n    return os.system(x)',
                 'def f(x):\n    return x.__class__.__mro__',
                 'def f(x):\n    return eval(x)',
                 'def f(x):\n    return [1] * 1000000000',
                 'def f(x):\n    return "%1000000000s" % x',
                 'def f(x):\n    while True:\n        pass',
                 'def f(x):\n    return f(x)',
                 'def f(x):\n    a = [0]\n    a[0] = a\n    return a']
        for code in cases:
            with self.subTest(code=code), patch('builtins.open', side_effect=AssertionError('host access')):
                self.assertIsNone(probe(code))

    def test_unknown_is_not_claimed_verified(self):
        self.assertEqual(compare_probes(None, probe(TOTAL)).status, 'inconclusive')
        self.assertEqual(compare_probes(probe('def f(a, b):\n    return a + b'),
                                        probe(TOTAL)).status, 'inconclusive')
        result = run_detection([UploadedFile('a.py', 'print("hello")'),
                                UploadedFile('b.java', 'System.out.println("hello");')],
                               0.5, HighScoreEngine())
        self.assertIn('behavior unverified', result.clone_pairs[0].description)

    def test_near_miss_score_does_not_depend_on_upload_order(self):
        a, b = ['ID_0', '+', 'ID_1', '*', '1'], ['ID_1', '*', '1', '+', 'ID_0']
        self.assertEqual(near_miss_similarity(a, b), near_miss_similarity(b, a))

    def test_utf8_and_multiline_tokens_are_read_exactly(self):
        line = 'café = "你好"'
        start = len('café = '.encode('utf-8'))
        self.assertEqual(index_to_code_token(((0, start), (0, len(line.encode('utf-8')))), [line]), '"你好"')
        self.assertEqual(index_to_code_token(((0, 0), (1, 5)), ['"""é', 'ß"""']), '"""é\nß"""')

    def test_missing_parser_cannot_return_corrupted_double_tokenized_input(self):
        from graphcodebert.engine import GraphCodeBERTEngine
        engine = GraphCodeBERTEngine.__new__(GraphCodeBERTEngine)
        engine._parsers = {}
        with self.assertRaisesRegex(RuntimeError, 'parser unavailable'):
            engine._extract_dataflow('def f(x): return x', 'python')

    def test_long_model_input_is_not_silently_truncated(self):
        from graphcodebert.engine import GraphCodeBERTEngine
        engine = GraphCodeBERTEngine.__new__(GraphCodeBERTEngine)
        engine._extract_dataflow = Mock(return_value=(['value'] * 600, []))
        engine._tokenizer = Mock()
        engine._tokenizer.tokenize.side_effect = lambda value: value.split()
        with self.assertRaisesRegex(ValueError, 'no truncated comparison'):
            engine._encode_fragment('synthetic source', 'python')

    def test_lower_model_score_needs_diverse_agreement_and_respects_user_threshold(self):
        class ModestScore(HighScoreEngine):
            def embed_batch(self, codes, langs):
                return np.array([[1., 0.], [.74, np.sqrt(1 - .74 ** 2)]])
        files = [UploadedFile('a.py', TOTAL), UploadedFile('b.py', 'def f(xs):\n    return sum(xs)')]
        self.assertEqual(run_detection(files, .5, ModestScore()).clone_pairs[0].clone_type, 'Type-4')
        self.assertFalse(run_detection(files, .8, ModestScore()).clone_pairs)
        with patch('detector.probe', return_value=None):
            self.assertFalse(run_detection(files, .5, ModestScore()).clone_pairs)

    def test_constant_sample_agreement_does_not_lower_threshold(self):
        evidence = compare_probes(probe('def f(x):\n    return 0'), probe('def g(y):\n    return 0'))
        self.assertEqual(evidence.diverse_outputs, 1)

    def test_shadowing_builtins_is_inconclusive_not_misinterpreted(self):
        self.assertIsNone(probe('def f(x):\n    sum = 1\n    return sum(x)'))

    def test_mutation_is_part_of_observed_behavior(self):
        a = 'def f(xs):\n    xs[0] = 0\n    return 1'
        b = 'def g(xs):\n    return 1'
        self.assertEqual(compare_probes(probe(a), probe(b)).status, 'different')

    def test_augmented_list_assignment_preserves_aliases_and_input_mutation(self):
        a = 'def f(xs):\n    other = xs\n    xs += [1]\n    return other'
        b = 'def g(xs):\n    other = xs\n    xs = xs + [1]\n    return other'
        self.assertEqual(compare_probes(probe(a), probe(b)).status, 'different')

    def test_generators_are_not_misread_as_lists(self):
        self.assertIsNone(probe('def f(xs):\n    return (x for x in xs)'))
        self.assertIsNone(probe('def f(xs):\n    return sum(x for x in xs)'))

    def test_late_builtin_binding_is_not_ignored(self):
        self.assertIsNone(probe('def f(xs):\n    return len(xs)\n    len = 3'))


if __name__ == '__main__':
    unittest.main()
