"""
graphcodebert/engine.py  (updated)

Key change: added  is_fine_tuned  property.
When False  → detector.py uses Stage-1 cosine similarity (works immediately).
When True   → detector.py uses pairwise GraphCodeBERT classifier (best accuracy).
"""

from __future__ import annotations
import os, sys, logging, hashlib
import numpy as np
from typing import Optional
from pathlib import Path

logger   = logging.getLogger(__name__)
_HERE        = Path(__file__).parent
_SAVED_MODEL = str(Path(__file__).parent.parent / "saved_models" / "model.bin")

MODEL_NAME  = "microsoft/graphcodebert-base"
CODE_LENGTH = 512
DFG_LENGTH  = 128
MAX_SEQ_LEN = CODE_LENGTH + DFG_LENGTH

_engine_instance: Optional["GraphCodeBERTEngine"] = None

def get_engine() -> "GraphCodeBERTEngine":
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = GraphCodeBERTEngine()
    return _engine_instance


class GraphCodeBERTEngine:
    def __init__(self, device: str = "auto", saved_model_path: str = _SAVED_MODEL):
        self._tokenizer        = None
        self._clf_model        = None
        self._parsers          = {}
        self._device           = None
        self._mock             = False
        self._saved_model_path = saved_model_path
        self._device_pref      = device
        self._model_loaded     = False
        self._load()

    # ── Fine-tuned flag ───────────────────────────────────────────────
    @property
    def is_fine_tuned(self) -> bool:
        """
        True only when a fine-tuned model.bin exists AND the model loaded.
        When False, detector.py uses embedding cosine similarity instead of
        the pairwise classifier, which still gives very good results.
        """
        return (
            not self._mock
            and self._model_loaded
            and os.path.isfile(self._saved_model_path)
        )

    # ── Loader ────────────────────────────────────────────────────────
    def _load(self):
        try:
            import torch
            from transformers import (
                RobertaTokenizer, RobertaConfig,
                RobertaForSequenceClassification,
            )

            self._device = (
                "cuda" if (self._device_pref == "auto" and torch.cuda.is_available())
                else "cpu"
            )
            logger.info(f"GraphCodeBERT on {self._device.upper()}")

            self._tokenizer = RobertaTokenizer.from_pretrained(MODEL_NAME)
            config          = RobertaConfig.from_pretrained(MODEL_NAME)

            sys.path.insert(0, str(_HERE.parent))
            from graphcodebert.model import Model

            encoder = RobertaForSequenceClassification.from_pretrained(
                MODEL_NAME, num_labels=2
            )
            self._clf_model = Model(encoder, config, self._tokenizer, args=_DummyArgs())
            self._clf_model.eval()
            self._clf_model.to(self._device)
            self._model_loaded = True

            if os.path.isfile(self._saved_model_path):
                state = torch.load(self._saved_model_path, map_location=self._device)
                self._clf_model.load_state_dict(state, strict=False)
                logger.info(
                    f"Fine-tuned weights loaded from {self._saved_model_path}\n"
                    "   → Pairwise classifier will be used (highest accuracy)"
                )
            else:
                logger.info(
                    "No fine-tuned weights found at saved_models/model.bin\n"
                    "   → Embedding cosine similarity will be used (still effective)\n"
                    "   → Run train.py on BigCloneBench to enable pairwise classifier"
                )

            self._load_parsers()

        except ImportError as exc:
            logger.warning(
                f"PyTorch/transformers not installed ({exc}). "
                "Mock embeddings active."
            )
            self._mock = True

    def _load_parsers(self):
        try:
            from tree_sitter import Language, Parser as TSParser
            import tree_sitter_python as tsp
            import tree_sitter_java   as tsj

            sys.path.insert(0, str(_HERE))
            from parser.DFG import DFG_python, DFG_java

            for lang_name, lang_module, dfg_fn in [
                ("python", tsp, DFG_python),
                ("java",   tsj, DFG_java),
            ]:
                try:
                    ts_lang = Language(lang_module.language())
                    try:
                        p = TSParser(ts_lang)
                    except TypeError:
                        p = TSParser()
                        p.set_language(ts_lang)
                    self._parsers[lang_name] = [p, dfg_fn]
                    logger.info(f"DFG parser ready for {lang_name}")
                except Exception as e:
                    logger.warning(f"DFG parser failed for {lang_name}: {e}")
        except Exception as exc:
            logger.warning(f"Parser loading failed ({exc}) — DFG will be empty")

    # ── DFG extraction ────────────────────────────────────────────────
    def _extract_dataflow(self, code: str, lang: str):
        if lang not in self._parsers:
            return self._tokenizer.tokenize(code)[:CODE_LENGTH], []
        sys.path.insert(0, str(_HERE))
        from parser.utils import (
            remove_comments_and_docstrings,
            tree_to_token_index,
            index_to_code_token,
        )
        parser = self._parsers[lang]
        try:
            code = remove_comments_and_docstrings(code, lang)
        except Exception:
            pass
        try:
            tree        = parser[0].parse(bytes(code, "utf8", errors="replace"))
            root        = tree.root_node
            tok_idx     = tree_to_token_index(root)
            lines       = code.split("\n")
            code_tokens = [index_to_code_token(x, lines) for x in tok_idx]
            idx2code    = {idx: (i, c) for i, (idx, c) in enumerate(zip(tok_idx, code_tokens))}
            try:
                dfg, _ = parser[1](root, idx2code, {})
            except Exception:
                dfg = []
            dfg  = sorted(dfg, key=lambda x: x[1])
            used = set()
            for d in dfg:
                if len(d[-1]) != 0:
                    used.add(d[1])
                for x in d[-1]:
                    used.add(x)
            dfg = [d for d in dfg if d[1] in used]
            return code_tokens, dfg
        except Exception as exc:
            logger.debug(f"DFG extraction error ({lang}): {exc}")
            return self._tokenizer.tokenize(code)[:CODE_LENGTH], []

    # ── Feature encoding ──────────────────────────────────────────────
    def _encode_fragment(self, code: str, lang: str) -> dict:
        import torch
        tokenizer         = self._tokenizer
        code_tokens, dfg  = self._extract_dataflow(code, lang)
        sub_tokens        = []
        ori2cur           = {-1: (0, 0)}
        for i, tok in enumerate(code_tokens):
            sub = (tokenizer.tokenize("@ " + tok)[1:]
                   if i != 0 else tokenizer.tokenize(tok))
            ori2cur[i] = (ori2cur[i - 1][1], ori2cur[i - 1][1] + len(sub))
            sub_tokens.extend(sub)

        keep       = CODE_LENGTH + DFG_LENGTH - 3 - min(len(dfg), DFG_LENGTH)
        sub_tokens = sub_tokens[:min(keep, 509)]
        src_tokens = [tokenizer.cls_token] + sub_tokens + [tokenizer.sep_token]
        src_ids    = tokenizer.convert_tokens_to_ids(src_tokens)
        pos_idx    = [i + tokenizer.pad_token_id + 1 for i in range(len(src_tokens))]

        dfg         = dfg[:CODE_LENGTH + DFG_LENGTH - len(src_tokens)]
        src_tokens += [x[0] for x in dfg]
        pos_idx    += [0] * len(dfg)
        src_ids    += [tokenizer.unk_token_id] * len(dfg)

        pad_len     = MAX_SEQ_LEN - len(src_ids)
        pos_idx    += [tokenizer.pad_token_id] * pad_len
        src_ids    += [tokenizer.pad_token_id] * pad_len

        rev         = {x[1]: i for i, x in enumerate(dfg)}
        dfg         = [x[:-1] + ([rev[i] for i in x[-1] if i in rev],) for x in dfg]
        return {
            "input_ids":    src_ids,
            "position_idx": pos_idx,
            "dfg_to_code":  [(ori2cur[x[1]][0]+1, ori2cur[x[1]][1]+1) for x in dfg],
            "dfg_to_dfg":   [x[-1] for x in dfg],
        }

    def _build_attn_mask(self, enc: dict) -> np.ndarray:
        L        = MAX_SEQ_LEN
        pos_idx  = enc["position_idx"]
        input_ids= enc["input_ids"]
        mask     = np.zeros((L, L), dtype=bool)
        node_idx = sum(p > 1  for p in pos_idx)
        max_len  = sum(p != 1 for p in pos_idx)
        mask[:node_idx, :node_idx] = True
        for i, tid in enumerate(input_ids):
            if tid in (0, 2):
                mask[i, :max_len] = True
        for i, (a, b) in enumerate(enc["dfg_to_code"]):
            if a < node_idx and b < node_idx:
                mask[i + node_idx, a:b] = True
                mask[a:b, i + node_idx] = True
        for i, nodes in enumerate(enc["dfg_to_dfg"]):
            for n in nodes:
                j = n + node_idx
                if j < L:
                    mask[i + node_idx, j] = True
        return mask

    # ── Public: Stage-1 embeddings ────────────────────────────────────
    def embed_batch(self, codes: list, langs: list) -> np.ndarray:
        if self._mock:
            return self._mock_embed(codes)
        import torch
        vectors = []
        for start in range(0, len(codes), 16):
            bc = codes[start: start + 16]
            bl = langs[start: start + 16]
            all_ids, all_pos, all_masks = [], [], []
            for code, lang in zip(bc, bl):
                enc   = self._encode_fragment(code, lang)
                amask = self._build_attn_mask(enc)
                all_ids.append(enc["input_ids"])
                all_pos.append(enc["position_idx"])
                all_masks.append(amask)
            ids_t  = torch.tensor(all_ids,             dtype=torch.long).to(self._device)
            pos_t  = torch.tensor(all_pos,             dtype=torch.long).to(self._device)
            mask_t = torch.tensor(np.array(all_masks), dtype=torch.bool).to(self._device)
            with torch.no_grad():
                nodes_mask = pos_t.eq(0)
                token_mask = pos_t.ge(2)
                word_emb   = self._clf_model.encoder.roberta.embeddings.word_embeddings(ids_t)
                n2t_mask   = (nodes_mask[:, :, None] & token_mask[:, None, :] & mask_t)
                n2t_mask   = n2t_mask.float() / (n2t_mask.float().sum(-1, keepdim=True) + 1e-10)
                avg_emb    = torch.einsum("abc,acd->abd", n2t_mask, word_emb)
                emb        = (word_emb * (~nodes_mask)[:, :, None]
                              + avg_emb * nodes_mask[:, :, None])
                out        = self._clf_model.encoder.roberta(
                    inputs_embeds=emb, attention_mask=mask_t,
                    position_ids=pos_t, token_type_ids=pos_t.eq(-1).long(),
                )[0]
                vectors.append(out[:, 0, :].cpu().numpy())
        return np.concatenate(vectors, axis=0).astype(np.float32)

    # ── Public: Stage-2 pairwise prediction (only when fine-tuned) ───
    def predict_pair(self, code_a, lang_a, code_b, lang_b) -> float:
        if self._mock:
            return self._mock_pair(code_a, code_b)
        return self.predict_batch([(code_a, lang_a, code_b, lang_b)])[0]

    def predict_batch(self, pairs: list) -> list:
        if self._mock:
            return [self._mock_pair(a, b) for a, _, b, _ in pairs]
        import torch
        probs = []
        for start in range(0, len(pairs), 8):
            chunk = pairs[start: start + 8]
            ids1, pos1, mask1 = [], [], []
            ids2, pos2, mask2 = [], [], []
            for ca, la, cb, lb in chunk:
                e1 = self._encode_fragment(ca, la)
                e2 = self._encode_fragment(cb, lb)
                ids1.append(e1["input_ids"]);   pos1.append(e1["position_idx"])
                ids2.append(e2["input_ids"]);   pos2.append(e2["position_idx"])
                mask1.append(self._build_attn_mask(e1))
                mask2.append(self._build_attn_mask(e2))
            def t(x, dt): return torch.tensor(np.array(x), dtype=dt).to(self._device)
            with torch.no_grad():
                prob = self._clf_model(
                    t(ids1, torch.long), t(pos1, torch.long), t(mask1, torch.bool),
                    t(ids2, torch.long), t(pos2, torch.long), t(mask2, torch.bool),
                )
            probs.extend(prob[:, 1].cpu().numpy().tolist())
        return probs

    # ── Mock helpers ──────────────────────────────────────────────────
    def _mock_embed(self, codes):
        vecs = []
        for c in codes:
            seed = int(hashlib.md5(c.encode()).hexdigest()[:8], 16)
            rng  = np.random.default_rng(seed)
            v    = rng.standard_normal(768).astype(np.float32)
            v   /= np.linalg.norm(v) + 1e-9
            vecs.append(v)
        return np.stack(vecs)

    def _mock_pair(self, a, b):
        import re, difflib
        ta = re.findall(r"\w+", a.lower())
        tb = re.findall(r"\w+", b.lower())
        return difflib.SequenceMatcher(None, ta, tb).ratio()


class _DummyArgs:
    code_length      = CODE_LENGTH
    data_flow_length = DFG_LENGTH
    n_gpu            = 0
