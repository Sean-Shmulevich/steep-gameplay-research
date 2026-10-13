#!/usr/bin/env python3
"""Check publication packaging, provenance hashes and local Markdown links.

This does not verify the original binary or game behavior.
"""
from pathlib import Path
import hashlib
import json
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
allowed = {'.md', '.txt', '.json', '.py'}
errors = []
files = []
for path in ROOT.rglob('*'):
    if '.git' in path.parts or '__pycache__' in path.parts:
        continue
    if path.is_symlink():
        errors.append(f'Symlink: {path.relative_to(ROOT)}')
    if not path.is_file():
        continue
    files.append(path)
    if path.name != '.gitignore' and path.suffix not in allowed:
        errors.append(f'Unapproved file type: {path.relative_to(ROOT)}')
    if path.stat().st_size > 1_000_000:
        errors.append(f'Unexpected large file: {path.relative_to(ROOT)}')
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeError:
        errors.append(f'Non-text file: {path.relative_to(ROOT)}')
        continue
    if '\x00' in text:
        errors.append(f'NUL byte: {path.relative_to(ROOT)}')
    if path.name != Path(__file__).name:
        for pattern in (r'gh[pousr]_[A-Za-z0-9]{20,}', r'sk-[A-Za-z0-9]{20,}', r'-----BEGIN .*PRIVATE KEY-----', r'/Users/[^/\s]+/'):
            if re.search(pattern, text):
                errors.append(f'Sensitive/local pattern: {path.relative_to(ROOT)}')
    if path.suffix == '.md':
        for target in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)', text):
            target = target.strip('<>')
            if re.match(r'https?://', target) or target.startswith('#'):
                continue
            local = unquote(target.split('#')[0])
            candidate = (path.parent / local).resolve()
            if not candidate.is_relative_to(ROOT) or not candidate.exists():
                errors.append(f'Broken/local external link: {path.relative_to(ROOT)} -> {target}')
for manifest_name in ('REFERENCE_MANIFEST.json', 'RECONSTRUCTION_SOURCES.json'):
    for item in json.loads((ROOT / manifest_name).read_text())['files']:
        path = ROOT / item['published']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['published_sha256']:
            errors.append(f'Reference provenance mismatch: {item["published"]}')
for item in json.loads((ROOT / 'contracts/systems.json').read_text())['systems']:
    if not (ROOT / item['source']).is_file():
        errors.append(f'Missing contract source: {item["source"]}')
manifest = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text())
for item in manifest['files']:
    path = ROOT / item['published']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['published_sha256']:
        errors.append(f'Provenance mismatch: {item["published"]}')
if errors:
    raise SystemExit('\n'.join(errors))
print(json.dumps({'ok': True, 'text_files': len(files), 'bytes': sum(p.stat().st_size for p in files),
                  'imported_research_documents': len(manifest['files']), 'game_files_included': False,
                  'scope': 'Packaging, hashes and local links; not binary or gameplay validation'}, indent=2))
