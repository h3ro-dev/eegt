"""Bind the loaded EEGT Python source files to the accepted run manifest."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys


def loaded_sources():
    """Return actual package source paths, including a package module run as main."""
    result = {}
    for key, module in tuple(sys.modules.items()):
        name = getattr(getattr(module, '__spec__', None), 'name', None) or key
        if key != '__main__' and name != 'eegt' and not name.startswith('eegt.'):
            continue
        filename = getattr(module, '__file__', None)
        if filename is None:  # namespace packages contain no executable source
            continue
        path = Path(filename).resolve()
        if key == '__main__' and path.name in ('prepare_validation.py', 'reproduce_validation.py'):
            relative = 'scripts/' + path.name
        elif name == 'eegt' or name.startswith('eegt.'):
            relative = name.replace('.', '/')
            relative += '/__init__.py' if path.name == '__init__.py' else '.py'
        else:
            continue
        if path.suffix != '.py' or not path.is_file():
            raise ValueError(f'loaded EEGT source is unavailable: {name}')
        result[relative] = path
    return result


def verify_loaded_sources(seal):
    bindings = dict(seal.get('inputs', {}))
    for model in seal.get('models', {}).values():
        bindings.update(model.get('vendor_sources', {}))
    for relative, path in loaded_sources().items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if bindings.get(relative) != actual:
            raise ValueError(f'loaded EEGT source differs from accepted freeze: {relative}')
