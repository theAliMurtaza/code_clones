"""Train a symmetric pairwise head on real frozen GraphCodeBERT CLS features.

CPU-friendly pilot; the encoder is NOT fine-tuned. Uses production preprocessing
and a locally running authenticated base-model service. The trained candidate is
never automatically installed as the live model. See TRAINING.md.
"""
import argparse
import hashlib
import json
import random
import time
from collections import Counter
from pathlib import Path
import numpy as np
import torch
from transformers import RobertaConfig
from graphcodebert.engine import GraphCodeBERTEngine, MODEL_NAME
from graphcodebert.model import RobertaClassificationHead
from graphcodebert.training_artifact import FORMAT, file_hash
from training_data import (read_archive, select_functions, induced_pairs,
                           metrics, select_threshold, serving_gate)
from deploy.laptop_model import api, LOCAL_URL, RUNTIME


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def embeddings(functions, selected, output, encoder_process='in-process'):
    preprocessor = GraphCodeBERTEngine.for_preprocessing()
    encoder = None
    if encoder_process == 'local-service':
        key = (RUNTIME / 'model-key.txt').read_text(encoding='utf-8').strip()
        info = api(LOCAL_URL, '/info', key, timeout=15)
        if info.get('protocol') != 1 or info.get('mode') != 'embedding':
            raise ValueError('Start the base laptop model before extracting training features')
    else:
        from config import get_settings
        get_settings().DETECTION_ENGINE = 'full'
        get_settings().BATCH_SIZE = 1
        encoder = GraphCodeBERTEngine(device='cpu', saved_model_path='')
        if not encoder.supports_semantics:
            raise RuntimeError('Base GraphCodeBERT could not load for training')
    cache = output / 'features'
    cache.mkdir()
    vectors, excluded = {}, {}
    ids = list(dict.fromkeys(i for values in selected.values() for i in values))
    for index, identifier in enumerate(ids):
        code = functions[identifier]
        try:
            preprocessor._encode_fragment(code, 'java')
        except (ValueError, RuntimeError) as exc:
            excluded[identifier] = str(exc)
            continue
        if encoder is None:
            response = api(LOCAL_URL, '/embed', key,
                           {'fragments': [{'code': code, 'language': 'java'}]}, timeout=180)
            vector = np.asarray(response.get('vectors'), dtype=np.float32)
        else:
            vector = encoder.embed_batch([code], ['java'])
        if vector.shape != (1, 768) or not np.all(np.isfinite(vector)) or np.linalg.norm(vector) <= 1e-9:
            raise ValueError('Invalid model vector; training stopped')
        vectors[identifier] = vector[0]
        np.save(cache / (hashlib.sha256(identifier.encode()).hexdigest() + '.npy'), vector[0])
        if (index + 1) % 10 == 0:
            print(f'Encoded {index+1}/{len(ids)} functions; usable={len(vectors)}', flush=True)
    return vectors, excluded


def score(head, pairs, vectors, batch_size):
    head.eval()
    scores = []
    with torch.no_grad():
        for offset in range(0, len(pairs), batch_size):
            batch = pairs[offset:offset+batch_size]
            a = torch.tensor(np.array([vectors[i] for i, _, _ in batch]))
            b = torch.tensor(np.array([vectors[j] for _, j, _ in batch]))
            scores.extend(torch.softmax(head.forward_vectors(a, b), dim=-1)[:, 1].tolist())
    return scores


def fit(head, pairs, vectors, args, output):
    optimizer = torch.optim.AdamW(head.parameters(), lr=args.lr, weight_decay=.01)
    train, valid = pairs['train'], pairs['valid']
    valid_labels = [r[2] for r in valid]
    best, history = None, []
    for epoch in range(args.epochs):
        head.train()
        order = list(range(len(train)))
        random.Random(args.seed + epoch).shuffle(order)
        loss_sum = 0.
        for offset in range(0, len(order), args.batch_size):
            batch = [train[i] for i in order[offset:offset+args.batch_size]]
            a = torch.tensor(np.array([vectors[i] for i, _, _ in batch]))
            b = torch.tensor(np.array([vectors[j] for _, j, _ in batch]))
            labels = torch.tensor([label for _, _, label in batch], dtype=torch.long)
            optimizer.zero_grad(set_to_none=True)
            loss = torch.nn.functional.cross_entropy(head.forward_vectors(a, b), labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(head.parameters(), 1.)
            optimizer.step()
            loss_sum += loss.item() * len(batch)
        predictions = score(head, valid, vectors, args.batch_size)
        threshold, measured = select_threshold(valid_labels, predictions, args.target_precision, args.min_recall)
        fallback = metrics(valid_labels, predictions, .5)
        rank = (threshold is not None, measured['recall'], measured['precision'], fallback['f1'])
        if best is None or rank > best:
            best = rank
            torch.save(head.state_dict(), output / 'model.bin')
            write_json(output / 'selection.json', {'epoch': epoch+1, 'threshold': threshold,
                                                   'validation': measured})
        row = {'epoch': epoch+1, 'train_loss': loss_sum/len(train),
               'threshold': threshold, 'validation': measured}
        history.append(row)
        print(json.dumps(row), flush=True)
    write_json(output / 'history.json', history)


def train(args):
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise ValueError('Use a new output directory; existing experiments are preserved')
    if output == Path(__file__).resolve().parent / 'saved_models':
        raise ValueError('Train in training_runs, not the live saved_models directory')
    output.mkdir(parents=True)
    started = time.time()
    functions, splits, archive_audit = read_archive(args.dataset_zip)
    selected, duplicates = select_functions(functions, splits,
        {'train': args.train_functions, 'valid': args.eval_functions, 'test': args.eval_functions}, args.seed)
    write_json(output / 'audit.json', {'archive_sha256': file_hash(args.dataset_zip),
        'archive': archive_audit, 'sample_function_ids': selected, 'duplicate_exclusions': duplicates,
        'scope': 'Java BigCloneBench binary clone labels; no Python accuracy claim', 'seed': args.seed})
    print('Archive audited. Extracting production GraphCodeBERT features.', flush=True)
    vectors, excluded = embeddings(functions, selected, output, args.encoder_process)
    write_json(output / 'encoding_exclusions.json', excluded)
    pairs = induced_pairs(splits, selected, vectors)
    del splits
    write_json(output / 'pairs.json', pairs)
    counts = {split: dict(Counter(str(row[2]) for row in rows)) for split, rows in pairs.items()}
    print('Eligible pair counts: ' + json.dumps(counts), flush=True)
    head = RobertaClassificationHead(RobertaConfig(hidden_size=768, hidden_dropout_prob=.1))
    fit(head, pairs, vectors, args, output)
    selection = json.loads((output / 'selection.json').read_text())
    head.load_state_dict(torch.load(output / 'model.bin', map_location='cpu', weights_only=True), strict=True)
    threshold = selection['threshold']
    # Test is evaluated once after epoch and threshold selection finish.
    test_scores = score(head, pairs['test'], vectors, args.batch_size)
    test_metrics = metrics([r[2] for r in pairs['test']], test_scores,
                           threshold if threshold is not None else 1.000001)
    reasons = serving_gate(selection['validation'], test_metrics, args.target_precision, args.min_recall)
    if threshold is None:
        reasons.append('No validation operating point met precision/recall targets')
    report = {'format': FORMAT, 'encoder': MODEL_NAME, 'training_mode': 'frozen_encoder_trained_pair_head',
        'threshold': threshold, 'selected_epoch': selection['epoch'],
        'validation': selection['validation'], 'test': test_metrics,
        'target_precision': args.target_precision, 'min_recall': args.min_recall,
        'eligible_for_serving': not reasons, 'gate_failures': reasons,
        'validated_language_pairs': ['java:java'] if not reasons else [],
        'weights_sha256': file_hash(output / 'model.bin'), 'pair_counts': counts,
        'encoded_functions': len(vectors), 'excluded_functions': len(excluded),
        'elapsed_seconds': round(time.time()-started, 1),
        'limitations': 'Pilot on sampled Java benchmark functions, not four-way or Python accuracy. '
                       'Clone labels do not prove universal behavioral equivalence. '
                       'Do not reuse this test set for tuning and call it untouched.'}
    write_json(output / 'model.json', report)
    write_json(output / 'test_predictions.json', [
        {'a': a, 'b': b, 'label': label, 'score': score_value}
        for (a, b, label), score_value in zip(pairs['test'], test_scores)])
    print(json.dumps(report, indent=2), flush=True)
    print('Candidate saved separately. The live laptop model has not been changed.', flush=True)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset_zip', required=True)
    p.add_argument('--output_dir', required=True)
    p.add_argument('--train_functions', type=int, default=256, help='0 uses all; default is a CPU pilot')
    p.add_argument('--eval_functions', type=int, default=128)
    p.add_argument('--epochs', type=int, default=20)
    p.add_argument('--batch_size', type=int, default=32)
    p.add_argument('--lr', type=float, default=1e-4)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--threads', type=int, default=2)
    p.add_argument('--encoder_process', choices=['in-process', 'local-service'], default='in-process')
    p.add_argument('--target_precision', type=float, default=.95)
    p.add_argument('--min_recall', type=float, default=.50)
    return p


if __name__ == '__main__':
    args = parser().parse_args()
    if (min(args.train_functions, args.eval_functions) < 0 or min(args.epochs, args.batch_size, args.threads) < 1
            or args.lr <= 0 or not 0 < args.target_precision <= 1 or not 0 < args.min_recall <= 1):
        raise SystemExit('Invalid training parameters')
    train(args)
