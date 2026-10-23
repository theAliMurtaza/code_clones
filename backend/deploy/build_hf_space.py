"""Build an allowlisted model-only Space folder. Never copy secrets or datasets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

BACKEND = Path(__file__).resolve().parents[1]


def build(output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Output already exists. Use a new folder to preserve previous exports.')
    sources = [(BACKEND / 'deploy/huggingface' / name, name)
               for name in ['app.py', 'README.md', 'requirements.txt']]
    sources += [(BACKEND / name, name) for name in ['config.py', 'semantic_service.py', 'zerogpu_service.py']]
    sources += [(BACKEND / 'graphcodebert' / name, f'graphcodebert/{name}')
                for name in ['__init__.py', 'engine.py', 'model.py', 'training_artifact.py']]
    sources += [(path, path.relative_to(BACKEND).as_posix())
                for path in sorted((BACKEND / 'graphcodebert/parser').glob('*.py'))]
    for source, _ in sources:
        if not source.is_file():
            raise FileNotFoundError(source)
    output.mkdir(parents=True)
    manifest = {}
    for source, name in sources:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        manifest[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Ready to upload: {output}\nFiles: {len(manifest)+1}; no .env files, secrets, datasets, or pilot weights copied.')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(BACKEND / 'deploy/.hf-space'))
    build(parser.parse_args().output)
