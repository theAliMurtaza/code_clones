"""Optional integration test against the installed GraphCodeBERT weights.

Run with RUN_MODEL_TESTS=1. Set HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1
to use cached weights only. This small smoke fixture is not an accuracy benchmark.
"""
import os
import unittest

from detector import UploadedFile, run_detection
from test_engine import FACT_REC, FACT_ITER, PYTHON_A, PYTHON_B, JAVA_A


@unittest.skipUnless(os.getenv('RUN_MODEL_TESTS') == '1', 'Opt-in real-model integration test')
class Type4ModelTests(unittest.TestCase):
    def test_semantic_examples_alongside_renamed_clone_and_unrelated_code(self):
        from graphcodebert.engine import GraphCodeBERTEngine
        engine = GraphCodeBERTEngine()
        self.assertTrue(engine.supports_semantics, 'Real model failed to load; fallback is not a semantic test')
        result = run_detection([
            UploadedFile('recursive.py', FACT_REC),
            UploadedFile('iterative.py', FACT_ITER),
            UploadedFile('sort.py', PYTHON_A),
            UploadedFile('renamed.py', PYTHON_B),
            UploadedFile('Sort.java', JAVA_A),
            UploadedFile('greet.py', 'def greet(name):\n    return "Hello " + name'),
        ], threshold=0.5, engine=engine)
        by_files = {frozenset((p.file_a, p.file_b)): p for p in result.clone_pairs}
        self.assertEqual(by_files[frozenset(('recursive.py', 'iterative.py'))].clone_type, 'Type-4')
        self.assertEqual(by_files[frozenset(('sort.py', 'Sort.java'))].clone_type, 'Type-4')
        self.assertEqual(by_files[frozenset(('sort.py', 'renamed.py'))].clone_type, 'Type-2')
        self.assertFalse(any('greet.py' in files for files in by_files))
        self.assertEqual(result.clone_pairs[0].clone_type, 'Type-4')
        self.assertGreater(result.semantic_pairs_checked, 0)


if __name__ == '__main__':
    unittest.main()
