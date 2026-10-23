"""Queued Gradio transport for ZeroGPU; reuse all semantic response validation."""
from concurrent.futures import TimeoutError
from urllib.parse import urlsplit
from config import get_settings
from graphcodebert.remote import RemoteSemanticEngine


class GradioSemanticEngine(RemoteSemanticEngine):
    def _request(self, method, path, payload=None):
        settings = get_settings()
        parsed = urlsplit(self.url)
        if (parsed.scheme != 'https' or not parsed.hostname.endswith('.hf.space')
                or parsed.path not in ('', '/') or parsed.port not in (None, 443)):
            raise ValueError('For Gradio, set SEMANTIC_API_URL to the Space https://...hf.space URL')
        try:
            from gradio_client import Client
        except ImportError:
            raise RuntimeError('Install gradio-client==2.3.0 on the backend for ZeroGPU') from None
        client, job = None, None
        try:
            # Keep the HF Authorization header separate from the model key.
            # No code, credentials, or remote exception body is printed to logs.
            client = Client(self.url, token=settings.HF_TOKEN or False,
                            headers={'X-Semantic-Api-Key': settings.SEMANTIC_API_KEY},
                            # Keep SDK worker defaults: one request also needs SSE
                            # readers and cancellation workers. The Space limits
                            # actual model concurrency to one.
                            verbose=False, download_files=False,
                            analytics_enabled=False, httpx_kwargs={'timeout': self.timeout})
            job = client.submit(*([] if payload is None else [payload]), api_name=path)
            data = job.result(timeout=self.timeout)
            if not isinstance(data, dict) or data.get('protocol') != 1:
                raise ValueError('Invalid model response')
            return data
        except TimeoutError:
            if job is not None:
                job.cancel()
            raise RuntimeError('ZeroGPU queue/inference timed out. Retry when the Space is ready; Type-4 was not completed.') from None
        except Exception:
            raise RuntimeError('ZeroGPU request failed. Check Space status/logs, HF_TOKEN, the shared model key, '
                               'and your daily GPU quota. Type-4 was not completed.') from None
        finally:
            if client is not None:
                client.close()
