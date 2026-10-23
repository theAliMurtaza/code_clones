"""Training regressions: no dataset downloads or claims about model accuracy."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile
import numpy as np
import torch
from transformers import RobertaConfig
from graphcodebert.model import RobertaClassificationHead
from graphcodebert.training_artifact import FORMAT, file_hash, load_head_artifact
from training_data import read_archive, induced_pairs, metrics, select_threshold, serving_gate
from train import fit, score


class TrainingTests(unittest.TestCase):
    def test_padding_removal_preserves_cls_vector_and_dataflow(self):
        from transformers import RobertaModel
        from graphcodebert.engine import GraphCodeBERTEngine, MAX_SEQ_LEN
        torch.set_num_threads(1)
        torch.manual_seed(9)
        roberta = RobertaModel(RobertaConfig(vocab_size=20,hidden_size=8,num_hidden_layers=1,
            num_attention_heads=2,intermediate_size=16,max_position_embeddings=514,
            hidden_dropout_prob=0,attention_probs_dropout_prob=0)).eval()
        engine = GraphCodeBERTEngine.__new__(GraphCodeBERTEngine)
        engine._mock=False; engine._lightweight=False; engine._device='cpu'
        engine._tokenizer=SimpleNamespace(pad_token_id=1)
        engine._clf_model=SimpleNamespace(encoder=SimpleNamespace(roberta=roberta))
        encoded={'input_ids':[0,4,5,2,3]+[1]*(MAX_SEQ_LEN-5),
                 'position_idx':[2,3,4,5,0]+[1]*(MAX_SEQ_LEN-5),
                 'dfg_to_code':[(1,3)],'dfg_to_dfg':[[]]}
        engine._encode_fragment=lambda code,lang:encoded
        mask=torch.tensor(engine._build_attn_mask(encoded))[None]
        ids=torch.tensor([encoded['input_ids']]); pos=torch.tensor([encoded['position_idx']])
        with torch.no_grad():
            word=roberta.embeddings.word_embeddings(ids)
            n2t=(pos.eq(0)[:,:,None]&pos.ge(2)[:,None,:]&mask).float()
            n2t=n2t/(n2t.sum(-1,keepdim=True)+1e-10)
            embedded=word*(~pos.eq(0))[:,:,None]+torch.einsum('abc,acd->abd',n2t,word)*pos.eq(0)[:,:,None]
            padded=roberta(inputs_embeds=embedded,attention_mask=mask,position_ids=pos,
                          token_type_ids=pos.eq(-1).long())[0][:,0,:].numpy()
        compact=engine.embed_batch(['ignored'],['java'])
        np.testing.assert_allclose(padded,compact,rtol=1e-5,atol=1e-6)

    def test_pair_head_is_order_invariant_and_learns(self):
        torch.manual_seed(5)
        head = RobertaClassificationHead(RobertaConfig(hidden_size=4, hidden_dropout_prob=0))
        a, b = torch.randn(6, 4), torch.randn(6, 4)
        self.assertTrue(torch.equal(head.forward_vectors(a, b), head.forward_vectors(b, a)))
        features = torch.stack((a, b), dim=1).reshape(12, 1, 4)
        self.assertTrue(torch.equal(head(features), head.forward_vectors(a, b)))
        before = head.out_proj.weight.detach().clone()
        loss = torch.nn.functional.cross_entropy(head.forward_vectors(a, b), torch.tensor([0,1,0,1,0,1]))
        loss.backward()
        torch.optim.SGD(head.parameters(), lr=.1).step()
        self.assertFalse(torch.equal(before, head.out_proj.weight))

    def test_threshold_handles_ties_and_no_qualifying_point(self):
        labels, scores = [1,0,1,0], [.9,.8,.8,.1]
        threshold, result = select_threshold(labels, scores, 1., .5)
        self.assertEqual(threshold, .9)
        self.assertEqual(result['fp'], 0)
        self.assertIsNone(select_threshold(labels, scores, 1., 1.)[0])
        for cutoff in [.1,.5,.8,.9]:
            expected = sum(s >= cutoff and y == 1 for s,y in zip(scores,labels))
            self.assertEqual(metrics(labels,scores,cutoff)['tp'], expected)

    def test_small_perfect_results_cannot_pass_gate(self):
        result = metrics([1,0], [.9,.1], .5)
        self.assertTrue(serving_gate(result, result, .95, .5))

    def test_archive_rejects_function_leakage_and_missing_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'input.zip'
            with ZipFile(path, 'w') as archive:
                archive.writestr('dataset/data.jsonl', '\n'.join(json.dumps({'idx':str(i),'func':f'int f{i}() {{ return {i}; }}'}) for i in range(6)))
                for split in ['train','valid','test']:
                    archive.writestr(f'dataset/{split}.txt', '0\t1\t0\n2\t3\t1\n')
            with self.assertRaisesRegex(ValueError, 'leakage'):
                read_archive(path)

    def test_reversed_pair_conflicts_fail(self):
        with self.assertRaisesRegex(ValueError, 'Contradictory'):
            induced_pairs({'train':[('a','b',1),('b','a',0)]}, {'train':['a','b']}, ['a','b'])

    def test_checkpoint_metadata_and_hash_required(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'model.bin'
            torch.save({'weights':torch.tensor([1.])}, path)
            metadata = {'format':FORMAT, 'encoder':'microsoft/graphcodebert-base',
                        'eligible_for_serving':False, 'threshold':.8,
                        'validated_language_pairs':['java:java'], 'weights_sha256':file_hash(path)}
            path.with_suffix('.json').write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'gate'):
                load_head_artifact(path)
            metadata['eligible_for_serving'] = True
            path.with_suffix('.json').write_text(json.dumps(metadata))
            self.assertEqual(load_head_artifact(path)[1]['threshold'], .8)
            torch.save({'weights':torch.tensor([2.])}, path)
            with self.assertRaisesRegex(ValueError, 'match'):
                load_head_artifact(path)

    def test_fit_uses_validation_not_test_and_saves_even_if_no_threshold_qualifies(self):
        torch.set_num_threads(1)
        torch.manual_seed(2)
        vectors = {str(i):np.array([i,1.,0.,-i],dtype=np.float32) for i in range(8)}
        pairs = {'train':[('0','1',1),('0','2',0)], 'valid':[('3','4',1),('3','5',0)]}
        # No test key: the fitting stage must not access test examples.
        head = RobertaClassificationHead(RobertaConfig(hidden_size=4, hidden_dropout_prob=0))
        args = SimpleNamespace(lr=.001,epochs=1,batch_size=2,seed=0,target_precision=1.,min_recall=1.)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            fit(head,pairs,vectors,args,output)
            self.assertTrue((output/'model.bin').exists())
            self.assertTrue((output/'selection.json').exists())
            self.assertEqual(len(score(head,pairs['valid'],vectors,2)),2)

    def test_evaluated_threshold_applies_and_counterexamples_still_win(self):
        from detector import run_detection, UploadedFile
        from test_detection_quality import FREQUENCY, SUM
        class Engine:
            is_fine_tuned=True
            classifier_threshold=.96
            validated_language_pairs=['java:java', 'python:python']
            def predict_batch(self,pairs):return [.95]*len(pairs)
        files=[UploadedFile('a.java','int sum(int[] xs) { int n=0; for(int x:xs) n+=x; return n; }'),
               UploadedFile('b.java','int total(int[] xs) { return Arrays.stream(xs).sum(); }')]
        result=run_detection(files,.5,Engine())
        self.assertFalse(result.clone_pairs)
        engine=Engine(); engine.classifier_threshold=.9
        result=run_detection(files,.5,engine)
        self.assertEqual(result.clone_pairs[0].clone_type,'Type-4')
        self.assertEqual(result.classifier_supported,1)
        self.assertFalse(run_detection([UploadedFile('a.py',FREQUENCY),UploadedFile('b.py',SUM)],.5,engine).clone_pairs)


if __name__ == '__main__':
    unittest.main()
