"""Space entry point. Import spaces BEFORE torch/transformers for ZeroGPU."""
import spaces
import os
from config import get_settings
from graphcodebert.engine import GraphCodeBERTEngine
from zerogpu_service import create_demo

settings = get_settings()
settings.DETECTION_ENGINE = 'full'
settings.BATCH_SIZE = 4
# Current ZeroGPU initializes CUDA emulation at startup. Load the model on CUDA
# here, not lazily inside @spaces.GPU. Real inference runs in decorated functions.
engine = GraphCodeBERTEngine(device='cuda')
demo = create_demo(engine, os.environ.get('SEMANTIC_API_KEY', ''), spaces.GPU)

if __name__ == '__main__':
    # Spaces may enable experimental SSR via its environment. This API service
    # does not need a Node renderer making additional API discovery requests.
    demo.launch(server_name='0.0.0.0', server_port=7860, show_error=False, ssr_mode=False)
