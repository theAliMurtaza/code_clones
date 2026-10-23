"""Standalone model server, without application accounts, database or Redis."""
from contextlib import asynccontextmanager
import logging
import secrets
from threading import Lock
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from config import get_settings

logger = logging.getLogger(__name__)


class FragmentInput(BaseModel):
    code: str = Field(min_length=1, max_length=131072)
    language: Literal["python", "java"]


class EmbeddingInput(BaseModel):
    fragments: list[FragmentInput] = Field(min_length=1, max_length=8)


class PairInput(BaseModel):
    a: FragmentInput
    b: FragmentInput


class PredictionInput(BaseModel):
    pairs: list[PairInput] = Field(min_length=1, max_length=4)


class BodyLimit:
    """Bound JSON bodies before parsing, including chunked requests."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        messages, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > 2 * 1024 * 1024:
                await send({"type": "http.response.start", "status": 413, "headers": []})
                await send({"type": "http.response.body", "body": b"Request too large"})
                return
            messages.append(message)
            if not message.get("more_body", False):
                break
        async def replay():
            return messages.pop(0) if messages else await receive()
        await self.app(scope, replay, send)


def create_app(engine_factory=None):
    lock = Lock()

    @asynccontextmanager
    async def lifespan(app):
        settings = get_settings()
        if len(settings.SEMANTIC_API_KEY) < 32:
            raise RuntimeError("Set a random SEMANTIC_API_KEY of at least 32 characters")
        app.state.api_key = settings.SEMANTIC_API_KEY
        if engine_factory is None:
            if settings.DETECTION_ENGINE != "full":
                raise RuntimeError("The model server requires DETECTION_ENGINE=full")
            from graphcodebert.engine import GraphCodeBERTEngine
            engine = GraphCodeBERTEngine()
        else:
            engine = engine_factory()
        if not engine.supports_semantics:
            raise RuntimeError("GraphCodeBERT failed to load; inspect model startup logs")
        app.state.engine = engine
        yield

    app = FastAPI(title="CloneScope Semantic Model", lifespan=lifespan)
    app.add_middleware(BodyLimit)

    def authorize(authorization: str = Header(default="")):
        expected = f"Bearer {app.state.api_key}"
        if not secrets.compare_digest(authorization.encode(), expected.encode()):
            raise HTTPException(401, "Invalid model API key")

    def info():
        engine = app.state.engine
        return {"protocol": 1, "mode": "classifier" if engine.is_fine_tuned else "embedding",
                "classifier_threshold": getattr(engine, 'classifier_threshold', None),
                "validated_language_pairs": getattr(engine, 'validated_language_pairs', [])}

    @app.get("/health")
    def health():
        return {"status": "ready"}

    @app.get("/info", dependencies=[Depends(authorize)])
    def model_info():
        return info()

    def infer(operation):
        if not lock.acquire(blocking=False):
            raise HTTPException(503, "Model is busy; retry the analysis")
        try:
            return operation()
        except Exception:
            logger.exception("Model inference failed")
            raise HTTPException(503, "Model inference failed; inspect server logs") from None
        finally:
            lock.release()

    @app.post("/embed", dependencies=[Depends(authorize)])
    def embed(payload: EmbeddingInput):
        vectors = infer(lambda: app.state.engine.embed_batch(
            [f.code for f in payload.fragments], [f.language for f in payload.fragments]))
        return {**info(), "vectors": vectors.tolist()}

    @app.post("/predict", dependencies=[Depends(authorize)])
    def predict(payload: PredictionInput):
        scores = infer(lambda: app.state.engine.predict_batch([
            (p.a.code, p.a.language, p.b.code, p.b.language) for p in payload.pairs]))
        return {**info(), "scores": scores}

    return app


app = create_app()
