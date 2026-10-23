"""Gradio API for the same inference protocol as the laptop model server."""
import json
import secrets
import gradio as gr
from pydantic import ValidationError
from semantic_service import EmbeddingInput, PredictionInput


def create_demo(engine, api_key, gpu_decorator):
    if len(api_key) < 32:
        raise RuntimeError('Add SEMANTIC_API_KEY as a Space secret (at least 32 characters)')
    if not engine.supports_semantics:
        raise RuntimeError('GraphCodeBERT failed to load; see startup logs')

    def authorize(request):
        supplied = request.headers.get('x-semantic-api-key', '') if request else ''
        if not secrets.compare_digest(supplied.encode(), api_key.encode()):
            raise gr.Error('Unauthorized model request')

    def metadata():
        return {'protocol': 1, 'mode': 'classifier' if engine.is_fine_tuned else 'embedding',
                'classifier_threshold': getattr(engine, 'classifier_threshold', None),
                'validated_language_pairs': getattr(engine, 'validated_language_pairs', [])}

    def validate(payload, schema):
        if len(json.dumps(payload).encode('utf-8')) > 2 * 1024 * 1024:
            raise gr.Error('Request too large')
        try:
            return schema.model_validate(payload)
        except ValidationError:
            raise gr.Error('Invalid code payload, language or batch size') from None

    @gpu_decorator(duration=60)
    def gpu_embed(fragments):
        return engine.embed_batch([f.code for f in fragments], [f.language for f in fragments]).tolist()

    @gpu_decorator(duration=60)
    def gpu_predict(pairs):
        return engine.predict_batch([(p.a.code, p.a.language, p.b.code, p.b.language) for p in pairs])

    def info(request: gr.Request):
        authorize(request)
        return metadata()

    def embed(payload, request: gr.Request):
        authorize(request)
        parsed = validate(payload, EmbeddingInput)
        try:
            return {**metadata(), 'vectors': gpu_embed(parsed.fragments)}
        except Exception:
            raise gr.Error('Model/GPU request failed. Check Space logs and GPU quota; no result was produced.') from None

    def predict(payload, request: gr.Request):
        authorize(request)
        parsed = validate(payload, PredictionInput)
        try:
            return {**metadata(), 'scores': gpu_predict(parsed.pairs)}
        except Exception:
            raise gr.Error('Model/GPU request failed. Check Space logs and GPU quota; no result was produced.') from None

    with gr.Blocks(title='CloneScope Model', analytics_enabled=False) as demo:
        gr.Markdown('# CloneScope model service\nAuthenticated inference for the CloneScope backend. '
                    'Upload code through your CloneScope application. No code or keys belong in this page.')
        request_json = gr.JSON(visible=False)
        response_json = gr.JSON(visible=False)
        gr.Button('Model info', visible=False).click(info, inputs=[], outputs=response_json,
                                                    api_name='info', queue=False)
        gr.Button('Embed', visible=False).click(embed, inputs=request_json, outputs=response_json,
                                               api_name='embed', concurrency_limit=1, concurrency_id='model')
        gr.Button('Predict', visible=False).click(predict, inputs=request_json, outputs=response_json,
                                                 api_name='predict', concurrency_limit=1, concurrency_id='model')
    return demo.queue(max_size=8, default_concurrency_limit=1)
