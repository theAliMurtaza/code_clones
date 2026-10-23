"""Run with the isolated Gradio environment; no GPU/model download is needed."""
import os
os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import numpy as np
import gradio as gr
from gradio_client import Client as RealClient
from config import get_settings
from graphcodebert.gradio_remote import GradioSemanticEngine
from zerogpu_service import create_demo
from deploy.build_hf_space import build
from deploy.upload_hf_space import verify_export

KEY = 'zerogpu-test-key-at-least-32-characters'


class Engine:
    supports_semantics = True
    is_fine_tuned = False
    def embed_batch(self, codes, langs):return np.ones((len(codes),768),dtype=np.float32)
    def predict_batch(self,pairs):return [.95]*len(pairs)


class ZeroTests(unittest.TestCase):
    def setUp(self):
        self.gpu_calls = 0
        def gpu(**kwargs):
            def decorate(fn):
                def run(*args):
                    self.gpu_calls += 1
                    return fn(*args)
                return run
            return decorate
        self.demo = create_demo(Engine(), KEY, gpu)
        self.endpoints = {v.api_name:v.fn for v in self.demo.fns.values()}
        self.request = Mock(headers={'x-semantic-api-key':KEY})
        self.addCleanup(self.demo.close)

    def test_auth_and_payload_validation_before_gpu(self):
        with self.assertRaises(gr.Error):
            self.endpoints['embed']({}, Mock(headers={}))
        with self.assertRaises(gr.Error):
            self.endpoints['embed']({'fragments':[]}, self.request)
        self.assertEqual(self.gpu_calls,0)
        output=self.endpoints['embed']({'fragments':[{'code':'pass','language':'python'}]},self.request)
        self.assertEqual(np.array(output['vectors']).shape,(1,768))
        self.assertEqual(self.gpu_calls,1)
        self.assertEqual(self.endpoints['info'](self.request)['protocol'],1)
        self.assertEqual(self.gpu_calls,1)

    def test_payload_and_prediction_batch_limits(self):
        with self.assertRaises(gr.Error):
            self.endpoints['embed']({'fragments':[{'code':'x','language':'python'}]*9},self.request)
        p={'a':{'code':'x','language':'python'},'b':{'code':'y','language':'java'}}
        self.assertEqual(self.endpoints['predict']({'pairs':[p]},self.request)['scores'],[.95])
        with self.assertRaises(gr.Error):
            self.endpoints['predict']({'pairs':[p]*5},self.request)

    def test_engine_selects_gradio_without_loading_local_model(self):
        from graphcodebert.engine import get_engine
        with patch.multiple(get_settings(), DETECTION_ENGINE='remote', SEMANTIC_API_TRANSPORT='gradio'), \
             patch('graphcodebert.gradio_remote.GradioSemanticEngine') as remote, \
             patch('graphcodebert.engine.GraphCodeBERTEngine') as local:
            self.assertIs(get_engine(),remote.return_value)
            local.assert_not_called()
        with patch.multiple(get_settings(), DETECTION_ENGINE='remote', SEMANTIC_API_TRANSPORT='invalid'):
            with self.assertRaises(ValueError):get_engine()

    def test_export_has_no_secrets_or_model_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=build(Path(tmp)/'space')
            verify_export(output)
            files={p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
            self.assertIn('app.py',files)
            self.assertIn('graphcodebert/parser/DFG.py',files)
            self.assertFalse(any('.env' in p or '.bin' in p or 'training_runs' in p for p in files))
            (output/'.env').write_text('private')
            with self.assertRaises(ValueError):verify_export(output)

    def test_real_gradio_client_queue_round_trip(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        self.demo.launch(server_name='127.0.0.1',server_port=port,prevent_thread_lock=True,quiet=True,ssr_mode=False)
        local=f'http://127.0.0.1:{port}'
        with patch.multiple(get_settings(),SEMANTIC_API_URL='https://example-clone.hf.space',
                            SEMANTIC_API_KEY=KEY,HF_TOKEN='',SEMANTIC_API_TIMEOUT=30), \
             patch('gradio_client.Client',side_effect=lambda url,**kw:RealClient(local,**kw)):
            engine=GradioSemanticEngine()
            self.assertEqual(engine.embed_batch(['x']*9,['python']*9).shape,(9,768))
            self.assertEqual(engine.predict_batch([('x','python','y','java')]*5),[.95]*5)
            self.assertEqual(self.gpu_calls,4)

    def test_failure_is_explicit_and_does_not_leak_credentials(self):
        with patch.multiple(get_settings(),SEMANTIC_API_URL='https://example-clone.hf.space',SEMANTIC_API_KEY=KEY), \
             patch('gradio_client.Client',side_effect=RuntimeError(KEY)):
            with self.assertRaisesRegex(RuntimeError,'Type-4 was not completed') as error:
                GradioSemanticEngine()
            self.assertNotIn(KEY,str(error.exception))


if __name__ == '__main__':unittest.main()
