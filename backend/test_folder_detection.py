"""Regression tests run without downloading a model or touching the app database."""
import os
os.environ['DATABASE_URL'] = 'sqlite://'

import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
import numpy as np

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from detector import UploadedFile, run_detection
from fragmenter import extract_fragments
import main
import models


class StructuralEngine:
    is_fine_tuned = False


class DetectionTests(unittest.TestCase):
    def detect(self, files):
        return run_detection([UploadedFile(name, code) for name, code in files],
                             threshold=0.8, engine=StructuralEngine())

    def test_short_renamed_functions_and_original_lines(self):
        a = '\n\ndef total(x, y):\n    return x + y\n'
        b = '# comment\ndef sum_values(a, b):\n    return a + b\n'
        pair, = self.detect([('root/a/main.py', a), ('root/b/main.py', b)]).clone_pairs
        self.assertEqual(pair.clone_type, 'Type-2')
        self.assertEqual(pair.lines_a, [3, 4])
        self.assertEqual(pair.lines_b, [2, 3])
        self.assertEqual(pair.code_a, '\n'.join(a.splitlines()[2:4]))

    def test_operator_changes_are_not_exact_or_renamed_clones(self):
        pairs = self.detect([('a.py', 'def f(x):\n    return x + 1'),
                             ('b.py', 'def f(x):\n    return x - 1')]).clone_pairs
        self.assertTrue(all(p.clone_type not in ('Type-1', 'Type-2') for p in pairs))

    def test_indentation_changes_are_not_exact_or_renamed_clones(self):
        pairs = self.detect([
            ('a.py', 'def f(x):\n    if x:\n        print(x)\n    return x'),
            ('b.py', 'def f(x):\n    if x:\n        print(x)\n        return x'),
        ]).clone_pairs
        self.assertTrue(all(p.clone_type not in ('Type-1', 'Type-2') for p in pairs))

    def test_comments_do_not_change_exact_clone_type(self):
        pair, = self.detect([('a.py', 'x = "# literal" # first'),
                             ('b.py', 'x = "# literal" # second')]).clone_pairs
        self.assertEqual(pair.clone_type, 'Type-1')

    def test_all_pairs_without_top_50_cutoff(self):
        pairs = self.detect([(f'dir{i}/same.py', 'value = input()') for i in range(60)]).clone_pairs
        self.assertEqual(len(pairs), 60 * 59 // 2)
        self.assertEqual(len({(p.file_a, p.file_b) for p in pairs}), len(pairs))

    def test_no_self_file_matches(self):
        self.assertEqual(self.detect([('a.py', 'def a():\n    return 1\ndef b():\n    return 1')]).clone_pairs, [])

    def test_unrelated_files_do_not_become_semantic_clones(self):
        self.assertEqual(self.detect([('a.py', 'print("hello")'),
                                      ('b.py', 'for value in values:\n    total += value')]).clone_pairs, [])

    def test_all_source_lines_covered_including_late_code(self):
        code = '\nvalue = 2\n\ndef short():\n    return value\n\n' + '\n'.join(f'x{i} = {i}' for i in range(160))
        frags = extract_fragments(code, 'all.py')
        covered = {n for f in frags for n in f.line_range}
        for n, line in enumerate(code.splitlines(), 1):
            if line.strip():
                self.assertIn(n, covered)
        for f in frags:
            self.assertEqual(f.code, '\n'.join(code.splitlines()[f.start_line - 1:f.end_line]))

    def test_java_short_method(self):
        code = 'class Example {\n    int answer() { return 42; }\n}'
        pairs = self.detect([('one/Example.java', code), ('two/Example.java', code)]).clone_pairs
        self.assertTrue(pairs)
        self.assertTrue(all(p.clone_type == 'Type-1' for p in pairs))

    def test_semantic_classifier_failure_is_not_an_empty_success(self):
        class BrokenEngine:
            is_fine_tuned = True
            def predict_batch(self, pairs):
                raise RuntimeError('inference failed')
        with self.assertRaisesRegex(RuntimeError, 'inference failed'):
            run_detection([UploadedFile('a.py', 'print("hello")'),
                           UploadedFile('b.java', 'System.out.println("hello");')], engine=BrokenEngine())

    def test_trained_classifier_can_report_cross_language_match(self):
        class TrainedEngine:
            is_fine_tuned = True
            def predict_batch(self, pairs):
                return [0.95] * len(pairs)
        result = run_detection([UploadedFile('a.py', 'print("hello")'),
                                UploadedFile('b.java', 'System.out.println("hello");')], engine=TrainedEngine())
        pair, = result.clone_pairs
        self.assertEqual(pair.clone_type, 'Type-4')
        self.assertTrue(pair.cross_language)

    def test_base_model_checks_low_overlap_pairs_once_and_keeps_other_types(self):
        class BaseEngine:
            is_fine_tuned = False
            supports_semantics = True
            calls = 0
            def embed_batch(self, codes, langs):
                self.calls += 1
                return np.array([[1., 0.], [1., 0.], [0.9, 0.43589], [0., 1.]])
        engine = BaseEngine()
        files = [UploadedFile('one.py', 'print("hello")'),
                 UploadedFile('copy.py', 'print("hello")'),
                 UploadedFile('two.java', 'System.out.println("hello");'),
                 UploadedFile('other.java', 'for(int i=0; i<10; i++) { total += i; }')]
        result = run_detection(files, threshold=0.5, engine=engine)
        self.assertEqual(engine.calls, 1)
        self.assertEqual(result.mode, 'embedding')
        self.assertEqual(result.semantic_pairs_checked, 5)
        self.assertEqual(result.clone_pairs[0].clone_type, 'Type-4')
        self.assertTrue(any(p.clone_type == 'Type-1' for p in result.clone_pairs))
        self.assertTrue(all('candidate' in p.description for p in result.clone_pairs if p.clone_type == 'Type-4'))
        self.assertFalse(any('other.java' in (p.file_a, p.file_b) for p in result.clone_pairs))
        high = run_detection(files, threshold=0.99, engine=engine)
        self.assertFalse(any(p.clone_type == 'Type-4' for p in high.clone_pairs))

    def test_lightweight_engine_is_reported_as_semantic_unavailable(self):
        result = self.detect([('a.py', 'print("hello")'), ('b.java', 'System.out.println("hello");')])
        self.assertEqual(result.analysis_info['mode'], 'structural')
        self.assertEqual(result.semantic_pairs_checked, 0)
        self.assertFalse(result.clone_pairs)

    def test_invalid_embeddings_fail_instead_of_returning_no_clones(self):
        class BaseEngine:
            is_fine_tuned = False
            supports_semantics = True
            def embed_batch(self, codes, langs):
                return np.zeros((len(codes), 3))
        with self.assertRaisesRegex(RuntimeError, 'empty embeddings'):
            run_detection([UploadedFile('a.py', 'print("hello")'),
                           UploadedFile('b.java', 'System.out.println("hello");')], engine=BaseEngine())


class FolderApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        models.Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        self.user = models.User(id=uuid.uuid4(), email='owner@example.com', name='Owner', hashed_password='unused')
        with self.sessions() as db:
            db.add(self.user)
            db.commit()
            db.refresh(self.user)
            db.expunge(self.user)
        def get_db():
            with self.sessions() as db:
                yield db
        main.app.dependency_overrides[main.get_db] = get_db
        main.app.dependency_overrides[main.get_current_user] = lambda: self.user
        self.session_patch = patch.object(main, 'SessionLocal', self.sessions)
        self.detection_patch = patch.object(main, 'run_detection', side_effect=lambda files, threshold:
                                            run_detection(files, threshold, engine=StructuralEngine()))
        self.session_patch.start()
        self.detection_patch.start()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        self.session_patch.stop()
        self.detection_patch.stop()
        main.app.dependency_overrides.clear()
        self.engine.dispose()

    def test_recursive_upload_results_full_source_and_owner_isolation(self):
        code = '\n\ndef add(a, b):\n    return a + b\n\nprint(add(1, 2))\n'
        paths = ['project/a/main.py', 'project/b/main.py']
        response = self.client.post('/api/detect', files=[('files', (p, code)) for p in paths])
        self.assertEqual(response.status_code, 202, response.text)
        job_id = response.json()['job_id']
        result = self.client.get(f'/api/jobs/{job_id}').json()
        self.assertEqual(result['status'], 'done', result)
        self.assertEqual(set(result['files']), set(paths))
        self.assertTrue(result['clone_pairs'])
        self.assertEqual(result['analysis_info']['mode'], 'structural')
        pair = result['clone_pairs'][0]
        self.assertEqual(pair['code_lines_a'][0]['n'], pair['lines_a'][0])
        source_url = f'/api/jobs/{job_id}/source'
        response = self.client.get(source_url, params={'path': paths[0]})
        self.assertEqual(response.json()['content'], code)
        self.assertEqual(self.client.get(source_url, params={'path': '../missing.py'}).status_code, 404)
        main.app.dependency_overrides[main.get_current_user] = lambda: models.User(id=uuid.uuid4())
        self.assertEqual(self.client.get(source_url, params={'path': paths[0]}).status_code, 404)

    def test_real_registration_login_and_authenticated_upload(self):
        # Exercise JWT -> UUID -> database lookup, not the user override.
        del main.app.dependency_overrides[main.get_current_user]
        credentials = {'email': 'signin@example.com', 'password': 'local-test-password'}
        registered = self.client.post('/api/auth/register', json={**credentials, 'name': 'Test'})
        self.assertEqual(registered.status_code, 201, registered.text)
        logged_in = self.client.post('/api/auth/login', json=credentials)
        self.assertEqual(logged_in.status_code, 200, logged_in.text)
        for token in [registered.json()['access_token'], logged_in.json()['access_token']]:
            headers = {'Authorization': f'Bearer {token}', 'Origin': 'http://localhost:5173'}
            for route in ['/api/me', '/api/jobs', '/api/stats']:
                response = self.client.get(route, headers=headers)
                self.assertEqual(response.status_code, 200, response.text)
            response = self.client.post('/api/detect', headers=headers,
                                        files=[('files', ('a.py', 'x = 1')), ('files', ('b.py', 'x = 1'))])
            self.assertEqual(response.status_code, 202, response.text)
            self.assertEqual(response.headers['access-control-allow-origin'], 'http://localhost:5173')
            result = self.client.get('/api/jobs/' + response.json()['job_id'], headers=headers)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()['status'], 'done')

    def test_malformed_token_subject_returns_401_not_server_error(self):
        from auth import create_access_token
        del main.app.dependency_overrides[main.get_current_user]
        token = create_access_token('invalid-user-id', 'test@example.com')
        response = self.client.get('/api/me', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 401, response.text)

    def test_local_scan_includes_nested_hidden_and_build_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ['main.py', 'nested/main.py', '.hidden/a.py', 'build/a.java']:
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('value = 123' if path.endswith('.py') else 'int value = 123;')
            (root / 'notes.txt').write_text('not source')
            response = self.client.post('/api/detect/folder', json={'folder_path': directory})
            self.assertEqual(response.status_code, 202, response.text)
            result = self.client.get('/api/jobs/' + response.json()['job_id']).json()
            self.assertEqual(result['status'], 'done', result)
            self.assertEqual(set(result['files']), {'main.py', 'nested/main.py', '.hidden/a.py', 'build/a.java'})

    def test_bad_path_metadata_and_duplicates_rejected(self):
        for metadata in ['{}', '[1]', '["a.py", "b.py"]', 'invalid']:
            response = self.client.post('/api/detect', files=[('files', ('a.py', 'x = 1'))],
                                        data={'paths_json': metadata})
            self.assertEqual(response.status_code, 422, response.text)
        response = self.client.post('/api/detect', files=[('files', ('a.py', 'x = 1'))] * 2)
        self.assertEqual(response.status_code, 422)

    def test_detection_failure_sets_failed_job_status(self):
        with patch.object(main, 'run_detection', side_effect=RuntimeError('inference failed')):
            response = self.client.post('/api/detect', files=[('files', ('a.py', 'x = 1'))])
        result = self.client.get('/api/jobs/' + response.json()['job_id']).json()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('inference failed', result['error'])

    def test_startup_adds_metadata_column_to_existing_jobs_table(self):
        from sqlalchemy import inspect, text
        old_engine = create_engine('sqlite://')
        with old_engine.begin() as connection:
            connection.execute(text('CREATE TABLE jobs (id VARCHAR PRIMARY KEY)'))
        with patch.object(main, 'engine', old_engine):
            main.create_tables()
            main.create_tables()  # Restarting must be safe.
        self.assertIn('analysis_info', {c['name'] for c in inspect(old_engine).get_columns('jobs')})
        old_engine.dispose()


if __name__ == '__main__':
    unittest.main()
