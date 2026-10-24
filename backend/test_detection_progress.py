"""Pipeline milestones must follow real work and stop on inference failures."""
import unittest
import numpy as np
from detector import UploadedFile, run_detection


class StructuralEngine:
    is_fine_tuned = False
    supports_semantics = False


class ProgressTests(unittest.TestCase):
    def test_structural_run_reports_filtered_count_and_skips_model(self):
        events = []
        result = run_detection([UploadedFile('a.py', 'def f(x):\n    return x + 1'),
                                UploadedFile('b.py', 'def f(x):\n    return x + 1')],
                               engine=StructuralEngine(), on_progress=events.append)
        self.assertEqual([e['stage'] for e in events],
                         ['extracting', 'tokenizing', 'structural', 'preparing'])
        self.assertEqual(events[-1]['total_fragments'], 2)
        self.assertEqual(events[-1]['skipped_stages'], ['semantic'])
        self.assertEqual(result.analysis_info['progress']['stage'], 'complete')
        self.assertEqual(len(result.clone_pairs), 1)

    def test_empty_comparison_skips_comparison_and_semantics(self):
        events = []
        result = run_detection([UploadedFile('a.py', 'def f(x):\n    return x + 1')],
                               engine=StructuralEngine(), on_progress=events.append)
        self.assertEqual([e['stage'] for e in events], ['extracting', 'tokenizing', 'preparing'])
        self.assertEqual(result.skipped_stages, ['structural', 'semantic'])

    def test_model_stage_precedes_inference_and_failure_cannot_finish(self):
        events = []
        class Model:
            is_fine_tuned = False
            supports_semantics = True
            fail = False
            def embed_batch(model, codes, languages):
                self.assertEqual(events[-1]['stage'], 'semantic')
                if model.fail:
                    raise RuntimeError('model unavailable')
                return np.eye(len(codes))
        files = [UploadedFile('a.py', 'def f(x):\n    return x + 1'),
                 UploadedFile('b.py', 'def g(values):\n    result = []\n    for v in values:\n        if v % 2 == 0:\n            result.append(v)\n    return result')]
        model = Model()
        run_detection(files, engine=model, on_progress=events.append)
        self.assertEqual([e['stage'] for e in events],
                         ['extracting', 'tokenizing', 'structural', 'semantic', 'preparing'])
        events.clear()
        model.fail = True
        with self.assertRaisesRegex(RuntimeError, 'model unavailable'):
            run_detection(files, engine=model, on_progress=events.append)
        self.assertEqual(events[-1]['stage'], 'semantic')


if __name__ == '__main__':
    unittest.main()
