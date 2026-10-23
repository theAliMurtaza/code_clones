"""Test the inference protocol, auth and detection without cloud credentials."""
import unittest
import os
from pathlib import Path
from unittest.mock import patch

os.environ['DATABASE_URL'] = 'sqlite://'

import httpx
import numpy as np
from fastapi.testclient import TestClient

from config import get_settings
from detector import UploadedFile, run_detection
from graphcodebert.remote import RemoteSemanticEngine
from semantic_service import create_app

KEY = "a-test-only-key-that-is-at-least-32-characters"
RealClient = httpx.Client


def all_types_inputs():
    demo = Path(__file__).resolve().parents[1] / 'examples' / 'all-types-demo'
    yield [UploadedFile('single_file.py', (demo / 'single_file.py').read_text())]
    folder = demo / 'folder'
    yield [UploadedFile(p.name, p.read_text()) for p in sorted(folder.rglob('*.py'))]
    yield [UploadedFile(p.relative_to(folder).as_posix(), p.read_text())
           for p in sorted(folder.rglob('*.py'))]


def assert_all_types(test, result):
    test.assertEqual({p.clone_type for p in result.clone_pairs},
                     {'Type-1', 'Type-2', 'Type-3', 'Type-4'})
    factorial_pairs = [p for p in result.clone_pairs
                       if ('def factorial(' in p.code_a and 'def fact(' in p.code_b)
                       or ('def fact(' in p.code_a and 'def factorial(' in p.code_b)]
    test.assertEqual(len(factorial_pairs), 1)
    test.assertEqual(factorial_pairs[0].clone_type, 'Type-4')
    test.assertGreater(result.semantic_pairs_checked, 0)
    for pair in result.clone_pairs:
        if pair.file_a == pair.file_b:
            test.assertTrue(pair.lines_a[1] < pair.lines_b[0]
                            or pair.lines_b[1] < pair.lines_a[0])


class FakeEngine:
    supports_semantics = True
    is_fine_tuned = False

    def embed_batch(self, codes, langs):
        return np.tile(np.array([1.] + [0.] * 767), (len(codes), 1))

    def predict_batch(self, pairs):
        return [0.95] * len(pairs)


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.settings = patch.multiple(get_settings(), SEMANTIC_API_KEY=KEY,
                                       SEMANTIC_API_URL="https://model.example.com")
        self.settings.start()
        self.addCleanup(self.settings.stop)
        self.model = FakeEngine()
        self.server = TestClient(create_app(lambda: self.model))
        self.server.__enter__()
        self.addCleanup(self.server.__exit__, None, None, None)

    def client(self, handler=None):
        def bridge(request):
            return self.server.request(request.method, request.url.path,
                                       headers=request.headers, content=request.content)
        transport = httpx.MockTransport(handler or bridge)
        return patch("graphcodebert.remote.httpx.Client",
                     side_effect=lambda **kw: RealClient(transport=transport, **kw))

    def test_remote_embeddings_feed_type4_pipeline(self):
        from test_detection_quality import FACTORIAL, RECURSIVE
        with self.client():
            engine = RemoteSemanticEngine()
            result = run_detection([
                UploadedFile("a.py", FACTORIAL),
                UploadedFile("b.py", RECURSIVE)], engine=engine)
        self.assertEqual(result.mode, "embedding")
        self.assertEqual(result.semantic_pairs_checked, 1)
        self.assertEqual(result.clone_pairs[0].clone_type, "Type-4")
        self.assertIn("candidate", result.clone_pairs[0].description)

    def test_all_four_types_are_retained_in_single_file_and_folder(self):
        with self.client():
            engine = RemoteSemanticEngine()
            for files in all_types_inputs():
                with self.subTest(files=len(files)):
                    assert_all_types(self, run_detection(files, threshold=0.5, engine=engine))

    def test_exact_and_renamed_pairs_are_classified_without_model_inference(self):
        with self.client(), patch.object(self.model, 'embed_batch') as embed, \
                patch.object(self.model, 'predict_batch') as predict:
            engine = RemoteSemanticEngine()
            result = run_detection([
                UploadedFile('a.py', 'def add(x, y):\n    return x + y'),
                UploadedFile('b.py', 'def add(x, y):\n    return x + y'),
                UploadedFile('c.py', 'def sum_values(a, b):\n    return a + b'),
            ], engine=engine)
            self.assertEqual(sorted(p.clone_type for p in result.clone_pairs),
                             ['Type-1', 'Type-2', 'Type-2'])
            embed.assert_not_called()
            predict.assert_not_called()

    def test_batches_preserve_all_fragments_and_classifier_pairs(self):
        self.model.is_fine_tuned = True
        with self.client():
            engine = RemoteSemanticEngine()
            self.assertTrue(engine.is_fine_tuned)
            self.assertEqual(engine.embed_batch(["pass"] * 17, ["python"] * 17).shape, (17, 768))
            self.assertEqual(engine.predict_batch([("pass", "python", "pass", "python")] * 9), [0.95] * 9)

    def test_evaluated_threshold_crosses_service_boundary(self):
        self.model.is_fine_tuned = True
        self.model.classifier_threshold = .97
        self.model.validated_language_pairs = ['java:java']
        with self.client():
            engine = RemoteSemanticEngine()
            self.assertEqual(engine.classifier_threshold, .97)
            self.assertEqual(engine.validated_language_pairs, ['java:java'])
            self.model.classifier_threshold = .9
            with self.assertRaisesRegex(RuntimeError, 'metadata changed'):
                engine.predict_batch([('pass','python','pass','python')])

    def test_invalid_evaluation_scope_is_rejected(self):
        self.model.is_fine_tuned = True
        self.model.validated_language_pairs = ['java:java']
        with self.client():
            with self.assertRaisesRegex(RuntimeError, 'metadata'):
                RemoteSemanticEngine()

    def test_bad_key_never_calls_model(self):
        with patch.object(self.model, "embed_batch") as embed:
            response = self.server.post("/embed", json={"fragments": [{"code": "pass", "language": "python"}]})
            self.assertEqual(response.status_code, 401)
            embed.assert_not_called()
        with patch.object(get_settings(), "SEMANTIC_API_KEY", "wrong-key"), self.client():
            with self.assertRaisesRegex(RuntimeError, "401"):
                RemoteSemanticEngine()

    def test_unavailable_remote_fails_instead_of_structural_fallback(self):
        def timeout(request):
            raise httpx.ReadTimeout("timeout", request=request)
        with self.client(timeout), patch.object(get_settings(), "DETECTION_ENGINE", "remote"):
            from graphcodebert.engine import get_engine
            with self.assertRaisesRegex(RuntimeError, "Type-4 was not completed"):
                get_engine()

    def test_invalid_vectors_and_model_changes_are_rejected(self):
        with self.client():
            engine = RemoteSemanticEngine()
            with patch.object(self.model, "embed_batch", return_value=np.zeros((1, 768))):
                with self.assertRaisesRegex(RuntimeError, "invalid embeddings"):
                    engine.embed_batch(["pass"], ["python"])
            self.model.is_fine_tuned = True
            with self.assertRaisesRegex(RuntimeError, "mode changed"):
                engine.embed_batch(["pass"], ["python"])

    def test_public_http_is_rejected(self):
        with patch.object(get_settings(), "SEMANTIC_API_URL", "http://model.example.com"):
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                RemoteSemanticEngine()

    def test_inference_error_is_reported_without_exception_details(self):
        with self.client():
            engine = RemoteSemanticEngine()
            with patch.object(self.model, "embed_batch", side_effect=RuntimeError("private details")):
                with self.assertRaisesRegex(RuntimeError, "503") as failure:
                    engine.embed_batch(["pass"], ["python"])
                self.assertNotIn("private details", str(failure.exception))

    def test_server_limits_payloads(self):
        headers = {"Authorization": f"Bearer {KEY}"}
        response = self.server.post("/embed", headers=headers,
                                    json={"fragments": [{"code": "pass", "language": "python"}] * 9})
        self.assertEqual(response.status_code, 422)
        response = self.server.post("/embed", headers=headers, content=b"x" * (2 * 1024 * 1024 + 1))
        self.assertEqual(response.status_code, 413)

    def test_server_refuses_structural_engine(self):
        self.model.supports_semantics = False
        with self.assertRaisesRegex(RuntimeError, "failed to load"):
            with TestClient(create_app(lambda: self.model)):
                pass


@unittest.skipUnless(os.getenv("RUN_MODEL_TESTS") == "1", "Opt-in real-model integration")
class RealRemoteModelTests(unittest.TestCase):
    def test_real_model_through_service_and_remote_client(self):
        from test_engine import FACT_REC, FACT_ITER, PYTHON_A, PYTHON_B, JAVA_A
        with patch.multiple(get_settings(), DETECTION_ENGINE="full", BATCH_SIZE=1,
                            SEMANTIC_API_KEY=KEY, SEMANTIC_API_URL="https://model.example.com"):
            with TestClient(create_app()) as server:
                def bridge(request):
                    return server.request(request.method, request.url.path,
                                          headers=request.headers, content=request.content)
                transport = httpx.MockTransport(bridge)
                with patch("graphcodebert.remote.httpx.Client",
                           side_effect=lambda **kw: RealClient(transport=transport, **kw)):
                    engine = RemoteSemanticEngine()
                    from test_detection_quality import FREQUENCY, SUM, TOTAL, FACTORIAL
                    for a, b in ((FREQUENCY, SUM), (TOTAL, FACTORIAL)):
                        with self.subTest(counterexample=a.splitlines()[0]):
                            rejection = run_detection([
                                UploadedFile('a.py', a), UploadedFile('nested/b.py', b)
                            ], threshold=0.5, engine=engine)
                            self.assertEqual(rejection.clone_pairs, [])
                    result = run_detection([
                        UploadedFile("recursive.py", FACT_REC),
                        UploadedFile("iterative.py", FACT_ITER),
                        UploadedFile("sort.py", PYTHON_A),
                        UploadedFile("renamed.py", PYTHON_B),
                        UploadedFile("Sort.java", JAVA_A),
                        UploadedFile("greet.py", 'def greet(name):\n    return "Hello " + name'),
                    ], threshold=0.5, engine=engine)
                    for files in all_types_inputs():
                        with self.subTest(demo_files=len(files)):
                            assert_all_types(self, run_detection(files, threshold=0.5, engine=engine))
                pairs = {frozenset((p.file_a, p.file_b)): p.clone_type for p in result.clone_pairs}
                self.assertEqual(pairs[frozenset(("recursive.py", "iterative.py"))], "Type-4")
                self.assertNotIn(frozenset(("sort.py", "Sort.java")), pairs)
                self.assertEqual(pairs[frozenset(("sort.py", "renamed.py"))], "Type-2")
                self.assertFalse(any("greet.py" in files for files in pairs))
                self.assertGreater(result.semantic_pairs_checked, 0)


if __name__ == "__main__":
    unittest.main()
