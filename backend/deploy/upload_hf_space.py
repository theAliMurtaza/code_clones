"""Explicitly upload a reviewed model-only export to an EXISTING Hugging Face Space."""
import argparse
import getpass
import hashlib
import json
from pathlib import Path
from huggingface_hub import HfApi


def verify_export(folder):
    manifest = json.loads((folder / 'build-manifest.json').read_text(encoding='utf-8'))
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual != set(manifest) | {'build-manifest.json'}:
        raise ValueError('Export contains extra/missing files. Rebuild it; never add secrets to the export.')
    for name, digest in manifest.items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Export changed since build. Rebuild before uploading.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--space', required=True, help='Your existing USERNAME/SPACE-NAME')
    parser.add_argument('--folder', default=str(Path(__file__).parent / '.hf-space'))
    args = parser.parse_args()
    folder = Path(args.folder).resolve()
    verify_export(folder)
    token = getpass.getpass('Hugging Face write token (hidden; not saved): ')
    api = HfApi(token=token)
    api.repo_info(args.space, repo_type='space')
    api.upload_folder(repo_id=args.space, repo_type='space', folder_path=str(folder),
                      commit_message='Deploy CloneScope ZeroGPU model API')
    print(f'Uploaded to https://huggingface.co/spaces/{args.space}. Check its build logs.')
