"""Authenticated inference client; never imports torch or substitutes fake vectors."""
from urllib.parse import urlsplit

import httpx
import numpy as np

from config import get_settings


class RemoteSemanticEngine:
    supports_semantics = True
    is_lightweight = False

    def __init__(self):
        settings = get_settings()
        self.url = settings.SEMANTIC_API_URL.rstrip("/")
        parsed = urlsplit(self.url)
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if (not parsed.hostname or parsed.username or parsed.password or parsed.query
                or parsed.fragment or parsed.scheme not in {"http", "https"}
                or (parsed.scheme != "https" and not local)):
            raise ValueError("Set SEMANTIC_API_URL to the HTTPS model service URL")
        if not settings.SEMANTIC_API_KEY:
            raise ValueError("SEMANTIC_API_KEY is required for remote inference")
        self.headers = {"Authorization": f"Bearer {settings.SEMANTIC_API_KEY}"}
        self.timeout = settings.SEMANTIC_API_TIMEOUT
        info = self._request("GET", "/info")
        self.mode = info.get("mode")
        if self.mode not in {"embedding", "classifier"}:
            raise RuntimeError("Remote model is not ready for Type-4 analysis")
        self.is_fine_tuned = self.mode == "classifier"
        self.classifier_threshold = info.get('classifier_threshold')
        self.validated_language_pairs = info.get('validated_language_pairs', [])
        if (self.classifier_threshold is not None and
                (type(self.classifier_threshold) not in (float, int)
                 or not 0 < self.classifier_threshold <= 1)):
            raise RuntimeError('Invalid remote classifier threshold')
        if (not isinstance(self.validated_language_pairs, list)
                or any(p not in ['java:java', 'python:python', 'java:python']
                       for p in self.validated_language_pairs)
                or (self.validated_language_pairs and
                    (not self.is_fine_tuned or self.classifier_threshold is None))):
            raise RuntimeError('Invalid remote classifier evaluation metadata')

    def _request(self, method, path, payload=None):
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
                response = client.request(method, self.url + path, headers=self.headers, json=payload)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or data.get("protocol") != 1:
                    raise ValueError("Invalid response")
                return data
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Remote semantic service returned HTTP {exc.response.status_code}. "
                "Check model service readiness and the shared API key; retry the analysis."
            ) from None
        except (httpx.HTTPError, ValueError):
            raise RuntimeError(
                "Cannot reach a ready semantic service. Check SEMANTIC_API_URL and "
                "model server logs, then retry the analysis. Type-4 was not completed."
            ) from None

    def _infer(self, path, payload):
        data = self._request("POST", path, payload)
        if data.get("mode") != self.mode:
            raise RuntimeError("Remote model mode changed during analysis; retry the job")
        if (data.get('classifier_threshold') != self.classifier_threshold
                or data.get('validated_language_pairs', []) != self.validated_language_pairs):
            raise RuntimeError('Remote classifier metadata changed during analysis; retry the job')
        return data

    def embed_batch(self, codes, langs):
        if len(codes) != len(langs):
            raise ValueError("Each fragment must have a language")
        vectors = []
        for start in range(0, len(codes), 8):
            fragments = [{"code": c, "language": l}
                         for c, l in zip(codes[start:start + 8], langs[start:start + 8])]
            data = self._infer("/embed", {"fragments": fragments})
            try:
                batch = np.asarray(data.get("vectors"), dtype=np.float32)
                valid = (batch.shape == (len(fragments), 768) and np.all(np.isfinite(batch))
                         and np.all(np.linalg.norm(batch, axis=1) > 1e-9))
            except (TypeError, ValueError):
                valid = False
            if not valid:
                raise RuntimeError("Remote model returned invalid embeddings")
            vectors.extend(batch)
        return np.asarray(vectors, dtype=np.float32).reshape(-1, 768)

    def predict_batch(self, pairs):
        scores = []
        for start in range(0, len(pairs), 4):
            batch = [{"a": {"code": a, "language": la}, "b": {"code": b, "language": lb}}
                     for a, la, b, lb in pairs[start:start + 4]]
            data = self._infer("/predict", {"pairs": batch})
            try:
                values = np.asarray(data.get("scores"), dtype=float)
                lower = 0 if self.is_fine_tuned else -1
                valid = (values.shape == (len(batch),) and np.all(np.isfinite(values))
                         and np.all((values >= lower) & (values <= 1)))
            except (TypeError, ValueError):
                valid = False
            if not valid:
                raise RuntimeError("Remote model returned invalid scores")
            scores.extend(values.tolist())
        return scores
