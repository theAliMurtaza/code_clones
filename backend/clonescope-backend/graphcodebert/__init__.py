"""
graphcodebert/
GraphCodeBERT integration package for CloneScope.

Public API:
    from graphcodebert import GraphCodeBERTEngine
    engine = GraphCodeBERTEngine()
    prob   = engine.predict_pair(code_a, "python", code_b, "java")
    vecs   = engine.embed_batch(["def foo(): ...", "public void bar(){}"], ["python","java"])
"""
from .engine import GraphCodeBERTEngine

__all__ = ["GraphCodeBERTEngine"]
