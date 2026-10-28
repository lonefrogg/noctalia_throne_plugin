#!/usr/bin/env python3
"""Check this repository's packaging, translation references and public files.

This is a local consistency check, not the upstream validator or a secret scanner.
It uses only Python 3.11's standard library and never contacts the network.
"""
import ast
import json
from pathlib import Path
import re
import struct
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'throne-vpn'
IGNORED = {'.git', '__pycache__', '.pytest_cache', '.venv'}


def flatten(data, prefix=''):
    result = {}
    for key, value in data.items():
        if '.' in key:
            raise ValueError('translation keys must be nested objects')
        name = prefix + key
        if isinstance(value, dict):
            result.update(flatten(value, name + '.'))
        elif isinstance(value, str):
            result[name] = value
        else:
            raise ValueError('translation values must be strings')
    return result


def webp_dimensions(raw):
    if raw[:4] != b'RIFF' or raw[8:12] != b'WEBP':
        raise ValueError('thumbnail is not WebP')
    offset = 12
    while offset + 8 <= len(raw):
        kind = raw[offset:offset + 4]
        size = struct.unpack_from('<I', raw, offset + 4)[0]
        data = raw[offset + 8:offset + 8 + size]
        if len(data) != size:
            raise ValueError('truncated WebP chunk')
        if kind == b'VP8X' and size >= 10:
            return 1 + int.from_bytes(data[4:7], 'little'), 1 + int.from_bytes(data[7:10], 'little')
        if kind == b'VP8L' and size >= 5 and data[0] == 0x2f:
            bits = int.from_bytes(data[1:5], 'little')
            return (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
        if kind == b'VP8 ' and size >= 10 and data[3:6] == b'\x9d\x01\x2a':
            width, height = struct.unpack_from('<HH', data, 6)
            return width & 0x3fff, height & 0x3fff
        offset += 8 + size + size % 2
    raise ValueError('missing WebP image dimensions')


def main():
    failures = []

    def check(condition, message):
        if not condition:
            failures.append(message)

    manifest = tomllib.loads((PLUGIN / 'plugin.toml').read_text(encoding='utf-8'))
    catalog = tomllib.loads((ROOT / 'catalog.toml').read_text(encoding='utf-8'))
    check(catalog.get('plugin') == [{key: value for key, value in manifest.items()
                                  if key not in ('setting', 'service', 'widget', 'panel')}],
          'standalone source catalog metadata must match plugin.toml')
    check(re.fullmatch(r'[a-z0-9][a-z0-9._-]*/throne-vpn', manifest['id']), 'invalid plugin ID')
    check(re.fullmatch(r'\d+\.\d+\.\d+', manifest['version']), 'version must be semver')
    check(manifest['plugin_api'] == 24, 'review API requirements when changing plugin_api')
    check(manifest['dependencies'] == ['python3', 'thronectl'], 'review declared dependencies')
    check(manifest['author'] == 'lonefrogg' and manifest['id'] == 'lonefrogg/throne-vpn', 'public owner and plugin namespace must match')

    translations = flatten(json.loads((PLUGIN / 'translations/en.json').read_text(encoding='utf-8')))
    settings = {item['key'] for item in manifest.get('setting', [])}
    references = set()
    for item in manifest.get('setting', []):
        references.update(item[key] for key in ('label_key', 'description_key') if key in item)
    for path in PLUGIN.glob('*.luau'):
        source = path.read_text(encoding='utf-8')
        references.update(re.findall(r'\btr\("([\w.]+)"\)', source))
        used = set(re.findall(r'noctalia\.getConfig\("(\w+)"\)', source))
        check(used <= settings, f'{path.name}: setting reference is not declared')
    check(references <= translations.keys(), 'translation references are missing: ' + ', '.join(sorted(references - translations.keys())))

    readme = (PLUGIN / 'README.md').read_text(encoding='utf-8')
    for kind in ('service', 'widget', 'panel'):
        for item in manifest[kind]:
            check((PLUGIN / item['entry']).is_file(), f'missing {kind} entry')
            check(f'`{item["id"]}`' in readme, f'undocumented {kind} entry')
    check('noctalia msg panel-toggle ' + manifest['id'] + ':panel' in readme, 'panel IPC example must match plugin ID')
    check(manifest['id'] + ':panel' in (PLUGIN / 'widget.luau').read_text(encoding='utf-8'), 'widget panel target must match plugin ID')
    for key in settings:
        check(f'`{key}`' in readme, f'undocumented setting: {key}')
    for required in ('LICENSE', 'permissions.md', 'backend.py', 'thumbnail.webp'):
        check((PLUGIN / required).is_file(), 'missing plugin file: ' + required)
    raw = (PLUGIN / 'thumbnail.webp').read_bytes()
    check(webp_dimensions(raw) == (960, 540), 'thumbnail must be 960 x 540')
    check(len(raw) <= 512 * 1024, 'thumbnail must be at most 512 KiB')
    backend = ast.parse((PLUGIN / 'backend.py').read_text(encoding='utf-8'))
    version = next(node.value.value for node in backend.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == 'VERSION' for target in node.targets))
    check(version == manifest['version'], 'helper and plugin versions must match')
    for node in ast.walk(backend):
        if isinstance(node, ast.Call):
            check(not any(arg.arg == 'shell' and not (isinstance(arg.value, ast.Constant) and arg.value.value is False)
                          for arg in node.keywords), 'backend must not enable subprocess shell mode')

    paths = [p for p in ROOT.rglob('*') if not any(part in IGNORED for part in p.relative_to(ROOT).parts)]
    for path in paths:
        relative = str(path.relative_to(ROOT))
        check(not path.is_symlink(), 'symlinks are not release files: ' + relative)
        if not path.is_file():
            continue
        check(path.suffix.lower() not in {'.key', '.pem', '.ovpn', '.db', '.log', '.zip', '.pyc'}
              and path.name not in {'api-key', 'api.key', '.env'}, 'unexpected private/build file: ' + relative)
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8'), filename=relative)
        if path.suffix.lower() in {'.md', '.py', '.toml', '.lua', '.luau', '.json', '.yml'}:
            source = path.read_text(encoding='utf-8')
            # Catch accidental machine paths without recording any real user's name.
            check(not re.search(r'/(?:home|Users)/[^/\s"\x27]+/', source), 'absolute user path found: ' + relative)
            check(not re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', source), 'private key material: ' + relative)
            check(not re.search(r'(?:vless|vmess|trojan|ss)://[^\s]+', source), 'subscription/profile URL found: ' + relative)
    for failure in failures:
        print('FAIL: ' + failure)
    if failures:
        return 1
    print(f'Release checks passed: {manifest["id"]} {manifest["version"]}.')
    print('This check does not establish desktop compatibility or guarantee the absence of secrets.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
